-- ======================================================================
-- PKG_LOAN_CALC  Liquidacion de cuota - Banco Horizonte (Oracle 11g+)
-- Autor: L.P.GOMEZ   Creado: 21/05/2011
-- Mant: 08/01/2015 LPG req 10233 | 17/06/2019 CAS req 12877
-- ======================================================================

CREATE TABLE loans (
  loan_id         VARCHAR2(11) PRIMARY KEY,
  customer_id     VARCHAR2(10) NOT NULL,
  status          CHAR(1)      NOT NULL,
  currency        VARCHAR2(3)  NOT NULL,
  principal       NUMBER(12)   NOT NULL,
  term_months     NUMBER(3)    NOT NULL,
  ea_rate         NUMBER(5,2)  NOT NULL,
  insurance_amt   NUMBER(9)    NOT NULL,
  first_due_date  DATE         NOT NULL,
  refi_date       DATE,
  refi_ea_rate    NUMBER(5,2)
);

CREATE TABLE loan_installments (
  loan_id           VARCHAR2(11) NOT NULL REFERENCES loans(loan_id),
  inst_no           NUMBER(3)    NOT NULL,
  status            VARCHAR2(4)  NOT NULL,   -- OPEN / PAID
  reversal_pending  CHAR(1)      DEFAULT 'N' NOT NULL,
  collection_fee    NUMBER(9,2)  DEFAULT 0 NOT NULL,
  CONSTRAINT pk_loan_inst PRIMARY KEY (loan_id, inst_no)
);

CREATE TABLE mora_rates   (valid_from DATE PRIMARY KEY, ea_rate     NUMBER(5,2));
CREATE TABLE legal_caps   (valid_from DATE PRIMARY KEY, max_ea_rate NUMBER(5,2));
CREATE TABLE bank_holidays(hday       DATE PRIMARY KEY);

CREATE TABLE calc_audit (
  calc_id    VARCHAR2(30) PRIMARY KEY,
  loan_id    VARCHAR2(11),
  inst_no    NUMBER(3),
  pay_date   DATE,
  total_due  NUMBER(14,2),
  created_at DATE DEFAULT SYSDATE
);

CREATE SEQUENCE seq_calc;

-- ----------------------------------------------------------------------
CREATE OR REPLACE PACKAGE PKG_LOAN_CALC AS

  TYPE T_RES IS RECORD (
    status     VARCHAR2(24),
    inst_no    NUMBER,
    due_date   DATE,
    eff_date   DATE,
    days       NUMBER,
    principal  NUMBER,
    reg_int    NUMBER,
    late_int   NUMBER,
    insurance  NUMBER,
    fees       NUMBER,
    total      NUMBER,
    applied    NUMBER,
    remaining  NUMBER,
    prin_rem   NUMBER,
    flags      VARCHAR2(6),
    calc_id    VARCHAR2(30)
  );

  FUNCTION CALC_CUOTA(p_loan    VARCHAR2,
                      p_inst    NUMBER,
                      p_pay_dt  DATE,
                      p_pay_amt NUMBER   DEFAULT 0,
                      p_ins     VARCHAR2 DEFAULT 'Y') RETURN T_RES;

  FUNCTION FMT(p_case VARCHAR2, p_loan VARCHAR2, r T_RES) RETURN VARCHAR2;

END PKG_LOAN_CALC;
/

CREATE OR REPLACE PACKAGE BODY PKG_LOAN_CALC AS

  c_cut CONSTANT NUMBER := 2000;

  PROCEDURE setf(p_f IN OUT VARCHAR2, p_pos NUMBER, p_ch VARCHAR2) IS
  BEGIN
    p_f := SUBSTR(p_f, 1, p_pos - 1) || p_ch || SUBSTR(p_f, p_pos + 1);
  END;

  FUNCTION is_bus(p_d DATE) RETURN BOOLEAN IS
    n NUMBER;
  BEGIN
    IF MOD(TRUNC(p_d) - DATE '1970-01-05', 7) >= 5 THEN
      RETURN FALSE;
    END IF;
    SELECT COUNT(*) INTO n FROM bank_holidays WHERE hday = TRUNC(p_d);
    RETURN n = 0;
  END;

  FUNCTION adj_bus(p_d DATE) RETURN DATE IS
    v DATE := TRUNC(p_d);
  BEGIN
    WHILE NOT is_bus(v) LOOP
      v := v + 1;
    END LOOP;
    RETURN v;
  END;

  FUNCTION nxt_bus(p_d DATE) RETURN DATE IS
    v DATE := TRUNC(p_d) + 1;
  BEGIN
    WHILE NOT is_bus(v) LOOP
      v := v + 1;
    END LOOP;
    RETURN v;
  END;

  FUNCTION mora_on(p_d DATE) RETURN NUMBER IS
    v NUMBER;
  BEGIN
    SELECT ea_rate INTO v FROM mora_rates
     WHERE valid_from = (SELECT MAX(valid_from) FROM mora_rates
                          WHERE valid_from <= p_d);
    RETURN v;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN RETURN NULL;
  END;

  FUNCTION cap_on(p_d DATE) RETURN NUMBER IS
    v NUMBER;
  BEGIN
    SELECT max_ea_rate INTO v FROM legal_caps
     WHERE valid_from = (SELECT MAX(valid_from) FROM legal_caps
                          WHERE valid_from <= p_d);
    RETURN v;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN RETURN NULL;
  END;

  PROCEDURE log_calc(p_id VARCHAR2, p_loan VARCHAR2, p_inst NUMBER,
                     p_dt DATE, p_tot NUMBER) IS
    PRAGMA AUTONOMOUS_TRANSACTION;
  BEGIN
    INSERT INTO calc_audit(calc_id, loan_id, inst_no, pay_date, total_due)
    VALUES (p_id, p_loan, p_inst, p_dt, p_tot);
    COMMIT;
  END;

  -- ------------------------------------------------------------------
  FUNCTION CALC_CUOTA(p_loan    VARCHAR2,
                      p_inst    NUMBER,
                      p_pay_dt  DATE,
                      p_pay_amt NUMBER   DEFAULT 0,
                      p_ins     VARCHAR2 DEFAULT 'Y') RETURN T_RES IS
    r      T_RES;
    lo     loans%ROWTYPE;
    v_old  NUMBER;
    v_st   VARCHAR2(4);
    v_rev  CHAR(1);
    v_fee  NUMBER;
    v_w    NUMBER;
    v_due  DATE;
    v_due2 DATE;
    v_eff  DATE;
    v_ea   NUMBER;
    v_im   NUMBER;
    v_pw   NUMBER;
    v_cf   NUMBER;
    v_pk   NUMBER;
    v_bal  NUMBER;
    v_int2 NUMBER;
    v_prn2 NUMBER;
    v_ins2 NUMBER;
    v_fee2 NUMBER;
    v_lt   NUMBER := 0;
    v_lt2  NUMBER;
    v_diff NUMBER;
    v_days NUMBER := 0;
    v_d    DATE;
    v_m    NUMBER;
    v_cap  NUMBER;
    v_rt   NUMBER;
    v_amt  NUMBER;
    v_rem  NUMBER := 0;
    TYPE t_n IS TABLE OF NUMBER INDEX BY PLS_INTEGER;
    cn     t_n;
  BEGIN
    r.status := 'OK';
    r.inst_no := p_inst;
    r.days := 0;
    r.principal := 0; r.reg_int := 0; r.late_int := 0; r.insurance := 0;
    r.fees := 0; r.total := 0; r.applied := 0; r.remaining := 0;
    r.prin_rem := 0;
    r.flags := '------';

    BEGIN
      SELECT * INTO lo FROM loans WHERE loan_id = p_loan;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        r.status := 'LOAN_NOT_FOUND';
        RETURN r;
    END;
    IF lo.status <> 'A' THEN
      r.status := 'LOAN_INACTIVE';
      RETURN r;
    END IF;
    IF lo.currency <> 'COP' THEN
      r.status := 'CURRENCY_INVALID';
      RETURN r;
    END IF;
    IF p_inst < 1 OR p_inst > lo.term_months THEN
      r.status := 'INSTALLMENT_NOT_FOUND';
      RETURN r;
    END IF;

    SELECT status, reversal_pending, collection_fee
      INTO v_st, v_rev, v_fee
      FROM loan_installments
     WHERE loan_id = p_loan AND inst_no = p_inst;
    SELECT MIN(inst_no) INTO v_old FROM loan_installments
     WHERE loan_id = p_loan AND (status = 'OPEN' OR reversal_pending = 'Y');

    v_w := p_inst;
    IF v_old IS NOT NULL AND v_old < p_inst THEN
      v_w := v_old;
      setf(r.flags, 1, 'O');
    ELSIF v_st = 'PAID' THEN
      IF v_rev = 'Y' THEN
        setf(r.flags, 2, 'R');
      ELSE
        r.status := 'PAID';
        RETURN r;
      END IF;
    END IF;

    -- vencimiento
    v_due := ADD_MONTHS(lo.first_due_date, v_w - 1);
    v_due2 := adj_bus(v_due);
    IF v_due2 <> v_due THEN
      setf(r.flags, 4, 'D');
    END IF;
    v_due := v_due2;

    -- fecha de pago
    v_eff := TRUNC(p_pay_dt);
    IF TO_NUMBER(TO_CHAR(p_pay_dt, 'HH24MI')) > c_cut THEN
      setf(r.flags, 3, 'C');
      v_eff := nxt_bus(v_eff);
    END IF;

    -- cuota francesa
    IF lo.refi_date IS NOT NULL AND v_due >= lo.refi_date THEN
      v_ea := lo.refi_ea_rate;
      setf(r.flags, 6, 'F');
    ELSE
      v_ea := lo.ea_rate;
    END IF;
    v_im  := POWER(1 + v_ea / 100, 1 / 12) - 1;
    v_pw  := POWER(1 + v_im, lo.term_months);
    v_cf  := lo.principal * v_im * v_pw / (v_pw - 1);
    v_pk  := POWER(1 + v_im, v_w - 1);
    v_bal := lo.principal * v_pk - v_cf * (v_pk - 1) / v_im;
    v_int2 := ROUND(ROUND(v_bal * v_im, 6), 2);
    v_prn2 := ROUND(ROUND(v_cf - v_bal * v_im, 6), 2);
    IF p_ins = 'Y' THEN
      v_ins2 := lo.insurance_amt;
    ELSE
      v_ins2 := 0;
    END IF;
    v_fee2 := v_fee;

    -- mora
    v_diff := v_eff - v_due;
    IF v_diff > 1 THEN
      v_days := v_diff - 1;
      FOR k IN 1 .. v_days LOOP
        v_d := v_due + 1 + k;
        v_m := mora_on(v_d);
        v_cap := cap_on(v_d);
        IF v_m IS NULL OR v_cap IS NULL THEN
          r.status := 'RATE_NOT_CONFIGURED';
          r.flags := '------';
          RETURN r;
        END IF;
        v_rt := LEAST(v_m, v_cap);
        v_lt := v_lt + v_prn2 * (POWER(1 + v_rt / 100, 1 / 360) - 1);
      END LOOP;
    END IF;
    v_lt2 := ROUND(ROUND(v_lt, 6), 2);

    -- total y abono
    r.total := v_fee2 + v_lt2 + v_int2 + v_ins2 + v_prn2;
    cn(1) := v_fee2;
    cn(2) := v_lt2;
    cn(3) := v_int2;
    cn(4) := v_ins2;
    cn(5) := v_prn2;
    v_amt := NVL(p_pay_amt, 0);
    FOR i IN 1 .. 5 LOOP
      IF v_amt >= cn(i) THEN
        v_amt := v_amt - cn(i);
        cn(i) := 0;
      ELSE
        cn(i) := cn(i) - v_amt;
        v_amt := 0;
      END IF;
      v_rem := v_rem + cn(i);
    END LOOP;
    IF v_amt > 0 THEN
      setf(r.flags, 5, 'X');
    END IF;

    r.inst_no   := v_w;
    r.due_date  := v_due;
    r.eff_date  := v_eff;
    r.days      := v_days;
    r.principal := v_prn2;
    r.reg_int   := v_int2;
    r.late_int  := v_lt2;
    r.insurance := v_ins2;
    r.fees      := v_fee2;
    r.applied   := r.total - v_rem;
    r.remaining := v_rem;
    r.prin_rem  := cn(5);
    SELECT 'CALC-' || TO_CHAR(SYSDATE, 'YYYYMMDD') || '-' ||
           LPAD(seq_calc.NEXTVAL, 5, '0')
      INTO r.calc_id FROM dual;
    log_calc(r.calc_id, p_loan, v_w, v_eff, r.total);
    RETURN r;
  END CALC_CUOTA;

  -- ------------------------------------------------------------------
  FUNCTION FMT(p_case VARCHAR2, p_loan VARCHAR2, r T_RES) RETURN VARCHAR2 IS
    FUNCTION m(x NUMBER) RETURN VARCHAR2 IS
    BEGIN
      RETURN TO_CHAR(x, 'FM0000000000.00');
    END;
    FUNCTION d(x DATE) RETURN VARCHAR2 IS
    BEGIN
      RETURN NVL(TO_CHAR(x, 'YYYYMMDD'), '00000000');
    END;
  BEGIN
    RETURN RPAD(p_case, 6) || '|' || RPAD(p_loan, 11) || '|' ||
           LPAD(r.inst_no, 3, '0') || '|' || RPAD(r.status, 24) || '|' ||
           d(r.due_date) || '|' || d(r.eff_date) || '|' ||
           LPAD(r.days, 3, '0') || '|' || m(r.principal) || '|' ||
           m(r.reg_int) || '|' || m(r.late_int) || '|' ||
           m(r.insurance) || '|' || m(r.fees) || '|' || m(r.total) || '|' ||
           m(r.applied) || '|' || m(r.remaining) || '|' ||
           m(r.prin_rem) || '|' || r.flags;
  END FMT;

END PKG_LOAN_CALC;
/

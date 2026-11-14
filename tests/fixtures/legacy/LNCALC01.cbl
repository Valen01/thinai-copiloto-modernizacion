       IDENTIFICATION DIVISION.
       PROGRAM-ID. LNCALC01.
       AUTHOR. J.R.MORALES.
       DATE-WRITTEN. 14/03/1998.
      *----------------------------------------------------------------*
      * LNCALC01  LIQUIDACION CUOTA PRESTAMO LIBRE INVERSION
      * BANCO HORIZONTE  -  ENTRADA LOANREQ.DAT  SALIDA LOANOUT.DAT
      *----------------------------------------------------------------*
      * 14/03/98 JRM  CREACION
      * 02/09/03 JRM  REQ 4471
      * 21/05/11 LPG  REQ 9120
      * 08/01/15 LPG  REQ 10233
      * 17/06/19 CAS  REQ 12877
      * 30/11/22 CAS  NO TOCAR REDONDEO, CONTABILIDAD CUADRA ASI
      *----------------------------------------------------------------*
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT LOANREQ ASSIGN TO 'LOANREQ.DAT'
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT LOANOUT ASSIGN TO 'LOANOUT.DAT'
               ORGANIZATION IS LINE SEQUENTIAL.
       DATA DIVISION.
       FILE SECTION.
       FD  LOANREQ.
       01  RQ-REC.
           05 RQ-CASE      PIC X(6).
           05 RQ-LOAN      PIC X(11).
           05 RQ-CUST      PIC X(10).
           05 RQ-LSTAT     PIC X.
           05 RQ-CCY       PIC X(3).
           05 RQ-PRIN      PIC 9(10).
           05 RQ-TERM      PIC 999.
           05 RQ-EA        PIC 99V99.
           05 RQ-INS       PIC 9(7).
           05 RQ-FDUE      PIC 9(8).
           05 RQ-INST      PIC 999.
           05 RQ-OLD       PIC 999.
           05 RQ-ISTAT     PIC X.
           05 RQ-REV       PIC X.
           05 RQ-PDATE     PIC 9(8).
           05 RQ-PTIME     PIC 9(4).
           05 RQ-PAMT      PIC 9(10)V99.
           05 RQ-FEE       PIC 9(7)V99.
           05 RQ-INSF      PIC X.
           05 RQ-RFDT      PIC 9(8).
           05 RQ-RFEA      PIC 99V99.
       FD  LOANOUT.
       01  OT-REC          PIC X(260).
       WORKING-STORAGE SECTION.
       77  W-EOF           PIC X     VALUE 'N'.
       77  W-X             PIC 99.
       77  W-BUS           PIC X.
       77  W-RTOK          PIC X.
       77  W-CPOK          PIC X.
       77  W-DOW           PIC 9.
       77  W-CD8           PIC 9(8).
       77  W-CHK           PIC 9(8).
       77  W-INSTW         PIC 999.
       77  W-DUEI          PIC 9(8).
       77  W-DUE8          PIC 9(8).
       77  W-EFFI          PIC 9(8).
       77  W-EFF8          PIC 9(8).
       77  W-FIRST         PIC 9(8).
       77  W-DIFF          PIC S9(8).
       77  W-DAYS          PIC 999.
       77  W-MM            PIC 9(6).
       77  W-NY            PIC 9(4).
       77  W-NM            PIC 99.
       77  W-MEA           PIC 99V99.
       77  W-CAP           PIC 99V99.
       77  W-EA            PIC 99V99.
       77  W-IM            COMP-2.
       77  W-PW            COMP-2.
       77  W-CF            COMP-2.
       77  W-PK            COMP-2.
       77  W-BAL           COMP-2.
       77  W-LF            COMP-2.
       77  W-IDF           COMP-2.
       77  W-INT6          PIC S9(11)V9(6).
       77  W-PRN6          PIC S9(11)V9(6).
       77  W-LT6           PIC S9(11)V9(6).
       77  W-INT2          PIC S9(11)V99.
       77  W-PRN2          PIC S9(11)V99.
       77  W-LT2           PIC S9(11)V99.
       77  W-INS2          PIC S9(11)V99.
       77  W-FEE2          PIC S9(11)V99.
       77  W-TOT           PIC S9(11)V99.
       77  W-AMT           PIC S9(11)V99.
       77  W-REM           PIC S9(11)V99.
       77  W-APL           PIC S9(11)V99.
       01  W-FLG           PIC X(6).
       01  W-D8            PIC 9(8).
       01  W-D8R REDEFINES W-D8.
           05 W-D8Y        PIC 9(4).
           05 W-D8M        PIC 99.
           05 W-D8D        PIC 99.
       01  W-CNT.
           05 W-CN         PIC S9(11)V99 OCCURS 5 TIMES.
      *
       01  W-HOL-T.
           05 FILLER       PIC 9(8) VALUE 20261102.
           05 FILLER       PIC 9(8) VALUE 20261116.
           05 FILLER       PIC 9(8) VALUE 20261208.
           05 FILLER       PIC 9(8) VALUE 20261225.
       01  W-HOL-R REDEFINES W-HOL-T.
           05 HD-DT        PIC 9(8) OCCURS 4 TIMES.
       01  W-MT-T.
           05 FILLER       PIC X(12) VALUE '202601012400'.
           05 FILLER       PIC X(12) VALUE '202611142600'.
       01  W-MT-R REDEFINES W-MT-T.
           05 MT-ENT OCCURS 2 TIMES.
              10 MT-FROM   PIC 9(8).
              10 MT-EA     PIC 99V99.
       01  W-CT-T.
           05 FILLER       PIC X(12) VALUE '202601012800'.
           05 FILLER       PIC X(12) VALUE '202612012500'.
       01  W-CT-R REDEFINES W-CT-T.
           05 CT-ENT OCCURS 2 TIMES.
              10 CT-FROM   PIC 9(8).
              10 CT-EA     PIC 99V99.
      *
       01  W-OUT.
           05 O-CASE       PIC X(6).
           05 FILLER       PIC X VALUE '|'.
           05 O-LOAN       PIC X(11).
           05 FILLER       PIC X VALUE '|'.
           05 O-INST       PIC 999.
           05 FILLER       PIC X VALUE '|'.
           05 O-ST         PIC X(24).
           05 FILLER       PIC X VALUE '|'.
           05 O-DUE        PIC 9(8).
           05 FILLER       PIC X VALUE '|'.
           05 O-EFF        PIC 9(8).
           05 FILLER       PIC X VALUE '|'.
           05 O-DAYS       PIC 999.
           05 FILLER       PIC X VALUE '|'.
           05 O-PRN        PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-INT        PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-LT         PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-INS        PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-FEE        PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-TOT        PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-APL        PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-REM        PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-PREM       PIC 9(10).99.
           05 FILLER       PIC X VALUE '|'.
           05 O-FLG        PIC X(6).
      *
       PROCEDURE DIVISION.
       0000-MAIN.
           OPEN INPUT LOANREQ OUTPUT LOANOUT.
           PERFORM UNTIL W-EOF = 'Y'
               READ LOANREQ
                   AT END MOVE 'Y' TO W-EOF
                   NOT AT END
                       PERFORM 1000-PRC THRU 1000-EXIT
                       MOVE W-OUT TO OT-REC
                       WRITE OT-REC
               END-READ
           END-PERFORM.
           CLOSE LOANREQ LOANOUT.
           STOP RUN.
      *
       1000-PRC.
           MOVE '------' TO W-FLG.
           MOVE RQ-CASE TO O-CASE.
           MOVE RQ-LOAN TO O-LOAN.
           MOVE RQ-INST TO O-INST.
           MOVE 'OK' TO O-ST.
           MOVE ZERO TO O-DUE O-EFF O-DAYS O-PRN O-INT O-LT O-INS
                        O-FEE O-TOT O-APL O-REM O-PREM.
           MOVE W-FLG TO O-FLG.
           IF RQ-LSTAT NOT = 'A'
               MOVE 'LOAN_INACTIVE' TO O-ST
               GO TO 1000-EXIT
           END-IF.
           IF RQ-CCY NOT = 'COP'
               MOVE 'CURRENCY_INVALID' TO O-ST
               GO TO 1000-EXIT
           END-IF.
           IF RQ-INST < 1 OR RQ-INST > RQ-TERM
               MOVE 'INSTALLMENT_NOT_FOUND' TO O-ST
               GO TO 1000-EXIT
           END-IF.
           MOVE RQ-INST TO W-INSTW.
           IF RQ-OLD < RQ-INST
               MOVE RQ-OLD TO W-INSTW
               MOVE 'O' TO W-FLG(1:1)
           ELSE
               IF RQ-ISTAT = 'P'
                   IF RQ-REV = 'Y'
                       MOVE 'R' TO W-FLG(2:1)
                   ELSE
                       MOVE 'PAID' TO O-ST
                       GO TO 1000-EXIT
                   END-IF
               END-IF
           END-IF.
      * VENCIMIENTO DE LA CUOTA
           MOVE RQ-FDUE TO W-D8.
           COMPUTE W-MM = W-D8Y * 12 + W-D8M - 1 + W-INSTW - 1.
           DIVIDE W-MM BY 12 GIVING W-NY REMAINDER W-NM.
           MOVE W-NY TO W-D8Y.
           COMPUTE W-D8M = W-NM + 1.
           COMPUTE W-DUEI = FUNCTION INTEGER-OF-DATE(W-D8).
           MOVE W-DUEI TO W-CHK.
           PERFORM 2300-CHKBUS.
           PERFORM UNTIL W-BUS = 'Y'
               ADD 1 TO W-DUEI
               MOVE 'D' TO W-FLG(4:1)
               MOVE W-DUEI TO W-CHK
               PERFORM 2300-CHKBUS
           END-PERFORM.
           COMPUTE W-DUE8 = FUNCTION DATE-OF-INTEGER(W-DUEI).
      * FECHA DE PAGO
           COMPUTE W-EFFI = FUNCTION INTEGER-OF-DATE(RQ-PDATE).
           IF RQ-PTIME > 2000
               MOVE 'C' TO W-FLG(3:1)
               ADD 1 TO W-EFFI
               MOVE W-EFFI TO W-CHK
               PERFORM 2300-CHKBUS
               PERFORM UNTIL W-BUS = 'Y'
                   ADD 1 TO W-EFFI
                   MOVE W-EFFI TO W-CHK
                   PERFORM 2300-CHKBUS
               END-PERFORM
           END-IF.
           COMPUTE W-EFF8 = FUNCTION DATE-OF-INTEGER(W-EFFI).
      * CUOTA FRANCESA
           IF RQ-RFDT > 0 AND W-DUE8 >= RQ-RFDT
               MOVE RQ-RFEA TO W-EA
               MOVE 'F' TO W-FLG(6:1)
           ELSE
               MOVE RQ-EA TO W-EA
           END-IF.
           COMPUTE W-IM = (1 + W-EA / 100) ** (1 / 12) - 1.
           COMPUTE W-PW = (1 + W-IM) ** RQ-TERM.
           COMPUTE W-CF = RQ-PRIN * W-IM * W-PW / (W-PW - 1).
           COMPUTE W-PK = (1 + W-IM) ** (W-INSTW - 1).
           COMPUTE W-BAL = RQ-PRIN * W-PK
                         - W-CF * (W-PK - 1) / W-IM.
           COMPUTE W-INT6 ROUNDED = W-BAL * W-IM.
           COMPUTE W-PRN6 ROUNDED = W-CF - W-BAL * W-IM.
           COMPUTE W-INT2 ROUNDED = W-INT6.
           COMPUTE W-PRN2 ROUNDED = W-PRN6.
           IF RQ-INSF = 'Y'
               MOVE RQ-INS TO W-INS2
           ELSE
               MOVE ZERO TO W-INS2
           END-IF.
           MOVE RQ-FEE TO W-FEE2.
      * MORA
           MOVE ZERO TO W-LF W-DAYS.
           COMPUTE W-DIFF = W-EFFI - W-DUEI.
           IF W-DIFF > 1
               COMPUTE W-DAYS = W-DIFF - 1
               COMPUTE W-FIRST = W-DUEI + 2
               PERFORM VARYING W-CHK FROM W-FIRST BY 1
                       UNTIL W-CHK > W-EFFI
                   COMPUTE W-CD8 = FUNCTION DATE-OF-INTEGER(W-CHK)
                   PERFORM 2400-RATE
                   IF W-RTOK = 'N' OR W-CPOK = 'N'
                       MOVE 'RATE_NOT_CONFIGURED' TO O-ST
                       MOVE '------' TO O-FLG
                       GO TO 1000-EXIT
                   END-IF
                   IF W-MEA > W-CAP
                       MOVE W-CAP TO W-MEA
                   END-IF
                   COMPUTE W-IDF = (1 + W-MEA / 100) ** (1 / 360) - 1
                   COMPUTE W-LF = W-LF + W-PRN2 * W-IDF
               END-PERFORM
           END-IF.
           COMPUTE W-LT6 ROUNDED = W-LF.
           COMPUTE W-LT2 ROUNDED = W-LT6.
      * TOTAL Y ABONO
           COMPUTE W-TOT = W-FEE2 + W-LT2 + W-INT2 + W-INS2 + W-PRN2.
           MOVE W-FEE2 TO W-CN(1).
           MOVE W-LT2  TO W-CN(2).
           MOVE W-INT2 TO W-CN(3).
           MOVE W-INS2 TO W-CN(4).
           MOVE W-PRN2 TO W-CN(5).
           MOVE RQ-PAMT TO W-AMT.
           PERFORM VARYING W-X FROM 1 BY 1 UNTIL W-X > 5
               IF W-AMT >= W-CN(W-X)
                   SUBTRACT W-CN(W-X) FROM W-AMT
                   MOVE ZERO TO W-CN(W-X)
               ELSE
                   SUBTRACT W-AMT FROM W-CN(W-X)
                   MOVE ZERO TO W-AMT
               END-IF
           END-PERFORM.
           IF W-AMT > 0
               MOVE 'X' TO W-FLG(5:1)
           END-IF.
           COMPUTE W-REM = W-CN(1) + W-CN(2) + W-CN(3)
                         + W-CN(4) + W-CN(5).
           MOVE W-INSTW TO O-INST.
           MOVE W-DUE8  TO O-DUE.
           MOVE W-EFF8  TO O-EFF.
           MOVE W-DAYS  TO O-DAYS.
           MOVE W-PRN2  TO O-PRN.
           MOVE W-INT2  TO O-INT.
           MOVE W-LT2   TO O-LT.
           MOVE W-INS2  TO O-INS.
           MOVE W-FEE2  TO O-FEE.
           MOVE W-TOT   TO O-TOT.
           COMPUTE W-APL = W-TOT - W-REM.
           MOVE W-APL   TO O-APL.
           MOVE W-REM   TO O-REM.
           MOVE W-CN(5) TO O-PREM.
           MOVE W-FLG   TO O-FLG.
       1000-EXIT.
           EXIT.
      *
       2300-CHKBUS.
           MOVE 'Y' TO W-BUS.
           COMPUTE W-DOW = FUNCTION MOD(W-CHK, 7).
           IF W-DOW = 6 OR W-DOW = 0
               MOVE 'N' TO W-BUS
           ELSE
               COMPUTE W-CD8 = FUNCTION DATE-OF-INTEGER(W-CHK)
               PERFORM VARYING W-X FROM 1 BY 1 UNTIL W-X > 4
                   IF W-CD8 = HD-DT(W-X)
                       MOVE 'N' TO W-BUS
                   END-IF
               END-PERFORM
           END-IF.
      *
       2400-RATE.
           MOVE 'N' TO W-RTOK.
           MOVE 'N' TO W-CPOK.
           PERFORM VARYING W-X FROM 1 BY 1 UNTIL W-X > 2
               IF W-CD8 >= MT-FROM(W-X)
                   MOVE MT-EA(W-X) TO W-MEA
                   MOVE 'Y' TO W-RTOK
               END-IF
               IF W-CD8 >= CT-FROM(W-X)
                   MOVE CT-EA(W-X) TO W-CAP
                   MOVE 'Y' TO W-CPOK
               END-IF
           END-PERFORM.

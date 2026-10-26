; gt6816_24lc16b_dump.bin  2048 bytes, base 0x0000
; traced 888 instructions covering 1915 bytes; 18 call targets

vec_0000:
  0000  02 00 49  LJMP loc_0049

vec_0003:
  0003  02 00 94  LJMP loc_0094
  0006  DB FFh,FFh,FFh,FFh,FFh   ; padding FF

vec_000B:
  000B  02 00 BA  LJMP loc_00BA
  000E  DB FFh,FFh,FFh,FFh,FFh   ; padding FF

vec_0013:
  0013  02 00 C9  LJMP loc_00C9
  0016  DB FFh,FFh,FFh,FFh,FFh   ; padding FF

vec_001B:
  001B  02 00 C9  LJMP loc_00C9
  001E  DB FFh,FFh,FFh,FFh,FFh   ; padding FF

vec_0023:
  0023  02 00 C9  LJMP loc_00C9
  0026  DB FFh,FFh,FFh,FFh,FFh   ; padding FF

vec_002B:
  002B  02 00 C9  LJMP loc_00C9
  002E  DB FFh,FFh   ; padding FF

loc_0030:    ; xref 00B7
  0030  90 FF 80  MOV DPTR,#FF80h  ; DCR
  0033  E0        MOVX A,@DPTR
  0034  D2 E0     SETB ACC.0
  0036  F0        MOVX @DPTR,A
  0037  00        NOP
  0038  00        NOP
  0039  00        NOP
  003A  12 00 CA  LCALL sub_00CA
  003D  32        RETI
  003E  DB FFh,FFh,02h,00h,49h   ; data/unreached

loc_0043:    ; xref 0046, 0091
  0043  75 87 01  MOV PCON,#01h
  0046  02 00 43  LJMP loc_0043

loc_0049:    ; xref 0000
  0049  E4        CLR A
  004A  F5 D0     MOV PSW,A
  004C  75 81 BF  MOV SP,#BFh
  004F  F8        MOV R0,A

loc_0050:    ; xref 0051
  0050  F6        MOV @R0,A
  0051  D8 FD     DJNZ R0,loc_0050
  0053  75 A8 05  MOV IE,#05h
  0056  75 88 05  MOV TCON,#05h
  0059  75 89 11  MOV TMOD,#11h
  005C  75 91 01  MOV SFR_91h,#01h
  005F  90 FF B0  MOV DPTR,#FFB0h  ; ISR
  0062  74 0E     MOV A,#0Eh
  0064  F0        MOVX @DPTR,A
  0065  90 FF CC  MOV DPTR,#FFCCh  ; UDCR
  0068  74 06     MOV A,#06h
  006A  F0        MOVX @DPTR,A
  006B  90 FF AF  MOV DPTR,#FFAFh  ; UIE1R
  006E  74 3F     MOV A,#3Fh
  0070  F0        MOVX @DPTR,A
  0071  90 FF AE  MOV DPTR,#FFAEh  ; UIE2R
  0074  74 14     MOV A,#14h
  0076  F0        MOVX @DPTR,A
  0077  90 FF C0  MOV DPTR,#FFC0h  ; UEIR
  007A  74 00     MOV A,#00h
  007C  F0        MOVX @DPTR,A
  007D  90 FF C8  MOV DPTR,#FFC8h  ; UECR
  0080  74 2F     MOV A,#2Fh
  0082  F0        MOVX @DPTR,A
  0083  12 04 45  LCALL sub_0445
  0086  90 FF AD  MOV DPTR,#FFADh  ; TIER
  0089  74 DF     MOV A,#DFh
  008B  F0        MOVX @DPTR,A
  008C  12 01 6B  LCALL sub_016B
  008F  D2 AF     SETB IE.7
  0091  02 00 43  LJMP loc_0043

loc_0094:    ; xref 0003
  0094  90 FF AD  MOV DPTR,#FFADh  ; TIER
  0097  E0        MOVX A,@DPTR
  0098  C2 E7     CLR ACC.7
  009A  F0        MOVX @DPTR,A
  009B  12 06 7C  LCALL sub_067C
  009E  20 00 08  JB 20h.0,loc_00A9
  00A1  90 FF AD  MOV DPTR,#FFADh  ; TIER
  00A4  E0        MOVX A,@DPTR
  00A5  D2 E7     SETB ACC.7
  00A7  F0        MOVX @DPTR,A
  00A8  32        RETI

loc_00A9:    ; xref 009E
  00A9  C2 00     CLR 20h.0
  00AB  90 FF 96  MOV DPTR,#FF96h  ; WDTRR
  00AE  74 68     MOV A,#68h
  00B0  F0        MOVX @DPTR,A
  00B1  90 FF 96  MOV DPTR,#FF96h  ; WDTRR
  00B4  74 01     MOV A,#01h
  00B6  F0        MOVX @DPTR,A
  00B7  02 00 30  LJMP loc_0030

loc_00BA:    ; xref 000B
  00BA  90 FF 96  MOV DPTR,#FF96h  ; WDTRR
  00BD  74 68     MOV A,#68h
  00BF  F0        MOVX @DPTR,A
  00C0  90 FF 96  MOV DPTR,#FF96h  ; WDTRR
  00C3  74 01     MOV A,#01h
  00C5  F0        MOVX @DPTR,A
  00C6  12 04 45  LCALL sub_0445

loc_00C9:    ; xref 0013, 001B, 0023, 002B
  00C9  32        RETI

sub_00CA:    ; xref 003A
  00CA  90 FF AD  MOV DPTR,#FFADh  ; TIER
  00CD  E0        MOVX A,@DPTR
  00CE  D2 E7     SETB ACC.7
  00D0  F0        MOVX @DPTR,A
  00D1  22        RET
  00D2  DB 12h,01h,10h,01h,00h,00h,00h,40h,B3h,07h,65h,04h,01h,00h,00h,02h   ; data/unreached
  00E2  DB 00h,01h,09h,02h,20h,00h,01h,01h,00h,A0h,FAh,09h,04h,00h,00h,02h   ; data/unreached
  00F2  DB FFh,FFh,FFh,00h,07h,05h,81h,02h,40h,00h,00h,07h,05h,02h,02h,40h   ; data/unreached
  0102  DB 00h,00h,04h,03h,09h,04h,26h,03h,36h,30h,30h,64h,70h,69h,20h,55h   ; data/unreached
  0112  DB 53h,42h,20h,53h,63h,61h,6Eh,6Eh,65h,72h   ; data/unreached

sub_011C:    ; xref 05AE
  011C  7A 3F     MOV R2,#3Fh
  011E  7B 80     MOV R3,#80h
  0120  7C 00     MOV R4,#00h
  0122  7D D2     MOV R5,#D2h
  0124  78 4A     MOV R0,#4Ah
  0126  75 91 00  MOV SFR_91h,#00h

loc_0129:    ; xref 0146
  0129  8C 83     MOV DPH,R4
  012B  8D 82     MOV DPL,R5
  012D  E4        CLR A
  012E  93        MOVC A,@A+DPTR
  012F  A3        INC DPTR
  0130  AC 83     MOV R4,DPH
  0132  AD 82     MOV R5,DPL
  0134  8A 83     MOV DPH,R2
  0136  8B 82     MOV DPL,R3
  0138  F0        MOVX @DPTR,A
  0139  A3        INC DPTR
  013A  B8 13 00  CJNE R0,#13h,loc_013D

loc_013D:    ; xref 013A
  013D  50 03     JNC loc_0142
  013F  E4        CLR A
  0140  F0        MOVX @DPTR,A
  0141  A3        INC DPTR

loc_0142:    ; xref 013D
  0142  AA 83     MOV R2,DPH
  0144  AB 82     MOV R3,DPL
  0146  D8 E1     DJNZ R0,loc_0129
  0148  90 3F 88  MOV DPTR,#3F88h
  014B  79 B7     MOV R1,#B7h
  014D  7A 06     MOV R2,#06h

loc_014F:    ; xref 0153
  014F  E7        MOV A,@R1
  0150  F0        MOVX @DPTR,A
  0151  09        INC R1
  0152  A3        INC DPTR
  0153  DA FA     DJNZ R2,loc_014F
  0155  90 3F 8F  MOV DPTR,#3F8Fh
  0158  79 BD     MOV R1,#BDh
  015A  E7        MOV A,@R1
  015B  F0        MOVX @DPTR,A
  015C  90 3F 99  MOV DPTR,#3F99h
  015F  79 BE     MOV R1,#BEh
  0161  E7        MOV A,@R1
  0162  F0        MOVX @DPTR,A
  0163  A3        INC DPTR
  0164  09        INC R1
  0165  E7        MOV A,@R1
  0166  F0        MOVX @DPTR,A
  0167  75 91 01  MOV SFR_91h,#01h
  016A  22        RET

sub_016B:    ; xref 008C
  016B  90 FF 87  MOV DPTR,#FF87h  ; ASR
  016E  E0        MOVX A,@DPTR
  016F  A2 E7     MOV C,ACC.7
  0171  92 18     MOV 23h.0,C
  0173  90 01 83  MOV DPTR,#0183h
  0176  78 09     MOV R0,#09h
  0178  79 B7     MOV R1,#B7h
  017A  E4        CLR A

loc_017B:    ; xref 0180
  017B  93        MOVC A,@A+DPTR
  017C  F7        MOV @R1,A
  017D  09        INC R1
  017E  A3        INC DPTR
  017F  E4        CLR A
  0180  D8 F9     DJNZ R0,loc_017B
  0182  22        RET
  0183  DB B3h,07h,65h,04h,01h,05h,01h,A0h,FAh   ; data/unreached

loc_018C:    ; xref 06E7
  018C  B4 21 03  CJNE A,#21h,loc_0192
  018F  02 01 F4  LJMP loc_01F4

loc_0192:    ; xref 018C
  0192  B4 22 03  CJNE A,#22h,loc_0198
  0195  02 02 07  LJMP loc_0207

loc_0198:    ; xref 0192
  0198  B4 23 03  CJNE A,#23h,loc_019E
  019B  02 02 19  LJMP loc_0219

loc_019E:    ; xref 0198
  019E  B4 24 03  CJNE A,#24h,loc_01A4
  01A1  02 02 24  LJMP loc_0224

loc_01A4:    ; xref 019E
  01A4  B4 27 03  CJNE A,#27h,loc_01AA
  01A7  02 02 37  LJMP loc_0237

loc_01AA:    ; xref 01A4
  01AA  B4 28 03  CJNE A,#28h,loc_01B0
  01AD  02 02 54  LJMP loc_0254

loc_01B0:    ; xref 01AA
  01B0  B4 29 03  CJNE A,#29h,loc_01B6
  01B3  02 02 67  LJMP loc_0267

loc_01B6:    ; xref 01B0
  01B6  02 02 8C  LJMP loc_028C

loc_01B9:    ; xref 071E
  01B9  B4 21 03  CJNE A,#21h,loc_01BF
  01BC  02 01 F0  LJMP loc_01F0

loc_01BF:    ; xref 01B9
  01BF  B4 22 03  CJNE A,#22h,loc_01C5
  01C2  02 02 06  LJMP loc_0206

loc_01C5:    ; xref 01BF
  01C5  B4 23 03  CJNE A,#23h,loc_01CB
  01C8  02 02 15  LJMP loc_0215

loc_01CB:    ; xref 01C5
  01CB  B4 24 03  CJNE A,#24h,loc_01D1
  01CE  02 02 25  LJMP loc_0225

loc_01D1:    ; xref 01CB
  01D1  B4 27 03  CJNE A,#27h,loc_01D7
  01D4  02 02 33  LJMP loc_0233

loc_01D7:    ; xref 01D1
  01D7  B4 28 03  CJNE A,#28h,loc_01DD
  01DA  02 02 55  LJMP loc_0255

loc_01DD:    ; xref 01D7
  01DD  B4 29 03  CJNE A,#29h,loc_01E3
  01E0  02 02 63  LJMP loc_0263

loc_01E3:    ; xref 01DD
  01E3  02 02 8D  LJMP loc_028D

loc_01E6:    ; xref 0798
  01E6  75 68 21  MOV 68h,#21h
  01E9  75 69 21  MOV 69h,#21h
  01EC  12 03 22  LCALL sub_0322
  01EF  22        RET

loc_01F0:    ; xref 01BC
  01F0  75 69 21  MOV 69h,#21h
  01F3  22        RET

loc_01F4:    ; xref 018F
  01F4  22        RET

loc_01F5:    ; xref 079E
  01F5  7E 00     MOV R6,#00h
  01F7  7F 09     MOV R7,#09h
  01F9  12 02 91  LCALL sub_0291
  01FC  75 68 22  MOV 68h,#22h
  01FF  75 69 22  MOV 69h,#22h
  0202  12 03 48  LCALL sub_0348
  0205  22        RET

loc_0206:    ; xref 01C2
  0206  22        RET

loc_0207:    ; xref 0195
  0207  75 69 22  MOV 69h,#22h
  020A  22        RET

loc_020B:    ; xref 07A4, 07B0
  020B  75 68 23  MOV 68h,#23h
  020E  75 69 23  MOV 69h,#23h
  0211  12 03 22  LCALL sub_0322
  0214  22        RET

loc_0215:    ; xref 01C8
  0215  75 69 23  MOV 69h,#23h
  0218  22        RET

loc_0219:    ; xref 019B
  0219  22        RET

loc_021A:    ; xref 07AA, 07B6
  021A  75 68 24  MOV 68h,#24h
  021D  75 69 24  MOV 69h,#24h
  0220  12 03 48  LCALL sub_0348
  0223  22        RET

loc_0224:    ; xref 01A1
  0224  22        RET

loc_0225:    ; xref 01CE
  0225  75 69 24  MOV 69h,#24h
  0228  22        RET

loc_0229:    ; xref 07BC
  0229  75 68 27  MOV 68h,#27h
  022C  75 69 27  MOV 69h,#27h
  022F  12 03 22  LCALL sub_0322
  0232  22        RET

loc_0233:    ; xref 01D4
  0233  75 69 27  MOV 69h,#27h
  0236  22        RET

loc_0237:    ; xref 01A7
  0237  12 02 A7  LCALL sub_02A7
  023A  E5 48     MOV A,48h
  023C  B4 69 03  CJNE A,#69h,loc_0242
  023F  12 02 BB  LCALL sub_02BB

loc_0242:    ; xref 023C
  0242  22        RET

loc_0243:    ; xref 07C2
  0243  7E 00     MOV R6,#00h
  0245  AF 48     MOV R7,48h
  0247  12 02 91  LCALL sub_0291
  024A  75 68 28  MOV 68h,#28h
  024D  75 69 28  MOV 69h,#28h
  0250  12 03 48  LCALL sub_0348
  0253  22        RET

loc_0254:    ; xref 01AD
  0254  22        RET

loc_0255:    ; xref 01DA
  0255  75 69 28  MOV 69h,#28h
  0258  22        RET

loc_0259:    ; xref 07C8
  0259  75 68 29  MOV 68h,#29h
  025C  75 69 29  MOV 69h,#29h
  025F  12 03 22  LCALL sub_0322
  0262  22        RET

loc_0263:    ; xref 01E0
  0263  75 69 29  MOV 69h,#29h
  0266  22        RET

loc_0267:    ; xref 01B3
  0267  12 02 A7  LCALL sub_02A7
  026A  22        RET

loc_026B:    ; xref 07CB
  026B  7E 00     MOV R6,#00h
  026D  AF 48     MOV R7,48h
  026F  12 02 91  LCALL sub_0291
  0272  E5 48     MOV A,48h
  0274  B4 73 05  CJNE A,#73h,loc_027C
  0277  12 03 8B  LCALL sub_038B
  027A  80 06     SJMP loc_0282

loc_027C:    ; xref 0274
  027C  B4 81 03  CJNE A,#81h,loc_0282
  027F  12 03 A9  LCALL sub_03A9

loc_0282:    ; xref 027A, 027C
  0282  75 68 2A  MOV 68h,#2Ah
  0285  75 69 2A  MOV 69h,#2Ah
  0288  12 03 48  LCALL sub_0348
  028B  22        RET

loc_028C:    ; xref 01B6
  028C  22        RET

loc_028D:    ; xref 01E3
  028D  75 69 2A  MOV 69h,#2Ah
  0290  22        RET

sub_0291:    ; xref 01F9, 0247, 026F, 04F1, 04FD, 0506, 0621, 064F
  0291  75 91 00  MOV SFR_91h,#00h
  0294  90 3F 00  MOV DPTR,#3F00h
  0297  EE        MOV A,R6
  0298  F0        MOVX @DPTR,A
  0299  A3        INC DPTR
  029A  EF        MOV A,R7
  029B  F0        MOVX @DPTR,A
  029C  E4        CLR A
  029D  79 3E     MOV R1,#3Eh

loc_029F:    ; xref 02A1
  029F  A3        INC DPTR
  02A0  F0        MOVX @DPTR,A
  02A1  D9 FC     DJNZ R1,loc_029F
  02A3  75 91 01  MOV SFR_91h,#01h
  02A6  22        RET

sub_02A7:    ; xref 0237, 0267
  02A7  75 91 00  MOV SFR_91h,#00h
  02AA  90 3F 40  MOV DPTR,#3F40h
  02AD  E0        MOVX A,@DPTR
  02AE  F5 48     MOV 48h,A
  02B0  A3        INC DPTR
  02B1  A3        INC DPTR
  02B2  E0        MOVX A,@DPTR
  02B3  FC        MOV R4,A
  02B4  A3        INC DPTR
  02B5  E0        MOVX A,@DPTR
  02B6  FD        MOV R5,A
  02B7  75 91 01  MOV SFR_91h,#01h
  02BA  22        RET

sub_02BB:    ; xref 023F
  02BB  E4        CLR A
  02BC  90 FF 83  MOV DPTR,#FF83h  ; M1SAHR
  02BF  F0        MOVX @DPTR,A
  02C0  90 FF 84  MOV DPTR,#FF84h  ; M1SALR
  02C3  F0        MOVX @DPTR,A
  02C4  90 FF 85  MOV DPTR,#FF85h  ; M2SAHR
  02C7  F0        MOVX @DPTR,A
  02C8  90 FF 86  MOV DPTR,#FF86h  ; M2SALR
  02CB  F0        MOVX @DPTR,A
  02CC  90 FF 82  MOV DPTR,#FF82h  ; D1TBLR
  02CF  F0        MOVX @DPTR,A
  02D0  74 20     MOV A,#20h
  02D2  90 FF 81  MOV DPTR,#FF81h  ; D1TBHR
  02D5  F0        MOVX @DPTR,A
  02D6  D2 00     SETB 20h.0
  02D8  22        RET

sub_02D9:    ; xref 02FA, 0332, 0358
  02D9  E4        CLR A
  02DA  90 FF C4  MOV DPTR,#FFC4h  ; DUTPS1R
  02DD  F0        MOVX @DPTR,A
  02DE  90 FF C3  MOV DPTR,#FFC3h  ; DUTPS2R
  02E1  F0        MOVX @DPTR,A
  02E2  90 FF C6  MOV DPTR,#FFC6h  ; DUTPC1R
  02E5  F0        MOVX @DPTR,A
  02E6  90 FF C5  MOV DPTR,#FFC5h  ; DUTPC2R
  02E9  F0        MOVX @DPTR,A
  02EA  22        RET

sub_02EB:    ; xref 0547, 0574, 0583, 0619, 0645, 066D, 0676
  02EB  75 70 00  MOV 70h,#00h

sub_02EE:    ; xref 0517, 05B1, 05D9, 060D, 0630, 065E
  02EE  90 FF A6  MOV DPTR,#FFA6h  ; EDLSAR
  02F1  E5 71     MOV A,71h
  02F3  F0        MOVX @DPTR,A
  02F4  90 FF A5  MOV DPTR,#FFA5h  ; EDHSAR
  02F7  74 3F     MOV A,#3Fh
  02F9  F0        MOVX @DPTR,A
  02FA  51 D9     ACALL sub_02D9
  02FC  E5 70     MOV A,70h
  02FE  90 FF C4  MOV DPTR,#FFC4h  ; DUTPS1R
  0301  F0        MOVX @DPTR,A
  0302  90 FF C0  MOV DPTR,#FFC0h  ; UEIR
  0305  74 00     MOV A,#00h
  0307  F0        MOVX @DPTR,A
  0308  90 FF C8  MOV DPTR,#FFC8h  ; UECR
  030B  74 2F     MOV A,#2Fh
  030D  F0        MOVX @DPTR,A
  030E  90 FF A9  MOV DPTR,#FFA9h  ; EDCR
  0311  74 E2     MOV A,#E2h
  0313  F0        MOVX @DPTR,A
  0314  90 FF C0  MOV DPTR,#FFC0h  ; UEIR
  0317  74 00     MOV A,#00h
  0319  F0        MOVX @DPTR,A
  031A  90 FF CA  MOV DPTR,#FFCAh  ; UERSR
  031D  E0        MOVX A,@DPTR
  031E  C2 E6     CLR ACC.6
  0320  F0        MOVX @DPTR,A
  0321  22        RET

sub_0322:    ; xref 01EC, 0211, 022F, 025F
  0322  90 FF BC  MOV DPTR,#FFBCh  ; URILB
  0325  E0        MOVX A,@DPTR
  0326  90 FF A6  MOV DPTR,#FFA6h  ; EDLSAR
  0329  F0        MOVX @DPTR,A
  032A  90 FF BD  MOV DPTR,#FFBDh  ; URIHB
  032D  E0        MOVX A,@DPTR
  032E  90 FF A5  MOV DPTR,#FFA5h  ; EDHSAR
  0331  F0        MOVX @DPTR,A
  0332  51 D9     ACALL sub_02D9
  0334  90 FF A9  MOV DPTR,#FFA9h  ; EDCR
  0337  74 EA     MOV A,#EAh
  0339  F0        MOVX @DPTR,A
  033A  90 FF C0  MOV DPTR,#FFC0h  ; UEIR
  033D  74 00     MOV A,#00h
  033F  F0        MOVX @DPTR,A
  0340  90 FF CA  MOV DPTR,#FFCAh  ; UERSR
  0343  E0        MOVX A,@DPTR
  0344  C2 E6     CLR ACC.6
  0346  F0        MOVX @DPTR,A
  0347  22        RET

sub_0348:    ; xref 0202, 0220, 0250, 0288
  0348  90 FF BC  MOV DPTR,#FFBCh  ; URILB
  034B  E0        MOVX A,@DPTR
  034C  90 FF A6  MOV DPTR,#FFA6h  ; EDLSAR
  034F  F0        MOVX @DPTR,A
  0350  90 FF BD  MOV DPTR,#FFBDh  ; URIHB
  0353  E0        MOVX A,@DPTR
  0354  90 FF A5  MOV DPTR,#FFA5h  ; EDHSAR
  0357  F0        MOVX @DPTR,A
  0358  51 D9     ACALL sub_02D9
  035A  90 FF BE  MOV DPTR,#FFBEh  ; URLLB
  035D  E0        MOVX A,@DPTR
  035E  54 C0     ANL A,#C0h
  0360  33        RLC A
  0361  33        RLC A
  0362  33        RLC A
  0363  F5 F0     MOV B,A
  0365  90 FF BF  MOV DPTR,#FFBFh  ; URLHB
  0368  E0        MOVX A,@DPTR
  0369  23        RL A
  036A  23        RL A
  036B  45 F0     ORL A,B
  036D  90 FF C6  MOV DPTR,#FFC6h  ; DUTPC1R
  0370  F0        MOVX @DPTR,A
  0371  90 FF C4  MOV DPTR,#FFC4h  ; DUTPS1R
  0374  74 40     MOV A,#40h
  0376  F0        MOVX @DPTR,A
  0377  90 FF A9  MOV DPTR,#FFA9h  ; EDCR
  037A  74 E2     MOV A,#E2h
  037C  F0        MOVX @DPTR,A
  037D  90 FF C0  MOV DPTR,#FFC0h  ; UEIR
  0380  74 00     MOV A,#00h
  0382  F0        MOVX @DPTR,A
  0383  90 FF CA  MOV DPTR,#FFCAh  ; UERSR
  0386  E0        MOVX A,@DPTR
  0387  C2 E6     CLR ACC.6
  0389  F0        MOVX @DPTR,A
  038A  22        RET

sub_038B:    ; xref 0277
  038B  75 91 00  MOV SFR_91h,#00h
  038E  90 3F 02  MOV DPTR,#3F02h
  0391  79 BB     MOV R1,#BBh
  0393  7A 02     MOV R2,#02h

loc_0395:    ; xref 0399
  0395  E7        MOV A,@R1
  0396  F0        MOVX @DPTR,A
  0397  A3        INC DPTR
  0398  09        INC R1
  0399  DA FA     DJNZ R2,loc_0395
  039B  79 B7     MOV R1,#B7h
  039D  7A 04     MOV R2,#04h

loc_039F:    ; xref 03A3
  039F  E7        MOV A,@R1
  03A0  F0        MOVX @DPTR,A
  03A1  A3        INC DPTR
  03A2  09        INC R1
  03A3  DA FA     DJNZ R2,loc_039F
  03A5  75 91 01  MOV SFR_91h,#01h
  03A8  22        RET

sub_03A9:    ; xref 027F
  03A9  75 91 00  MOV SFR_91h,#00h
  03AC  90 3F 04  MOV DPTR,#3F04h
  03AF  79 03     MOV R1,#03h
  03B1  E9        MOV A,R1
  03B2  F0        MOVX @DPTR,A
  03B3  E4        CLR A
  03B4  A3        INC DPTR
  03B5  F0        MOVX @DPTR,A
  03B6  A3        INC DPTR
  03B7  F0        MOVX @DPTR,A
  03B8  75 91 01  MOV SFR_91h,#01h
  03BB  22        RET

sub_03BC:    ; xref 06CA
  03BC  90 FF CC  MOV DPTR,#FFCCh  ; UDCR
  03BF  74 07     MOV A,#07h
  03C1  F0        MOVX @DPTR,A
  03C2  90 FF FF  MOV DPTR,#FFFFh
  03C5  74 20     MOV A,#20h
  03C7  F0        MOVX @DPTR,A
  03C8  90 FF FD  MOV DPTR,#FFFDh
  03CB  74 00     MOV A,#00h
  03CD  F0        MOVX @DPTR,A
  03CE  90 FF CC  MOV DPTR,#FFCCh  ; UDCR
  03D1  E0        MOVX A,@DPTR
  03D2  C2 E2     CLR ACC.2
  03D4  F0        MOVX @DPTR,A
  03D5  90 FF 95  MOV DPTR,#FF95h  ; GPIODR
  03D8  74 20     MOV A,#20h
  03DA  F0        MOVX @DPTR,A
  03DB  90 FF 94  MOV DPTR,#FF94h  ; GPIOCR
  03DE  74 40     MOV A,#40h
  03E0  F0        MOVX @DPTR,A
  03E1  75 90 FF  MOV P1,#FFh
  03E4  90 FF A2  MOV DPTR,#FFA2h  ; PPHDR
  03E7  74 0A     MOV A,#0Ah
  03E9  F0        MOVX @DPTR,A
  03EA  E4        CLR A
  03EB  90 FF 9F  MOV DPTR,#FF9Fh  ; SCR
  03EE  74 01     MOV A,#01h
  03F0  F0        MOVX @DPTR,A
  03F1  44 23     ORL A,#23h
  03F3  F0        MOVX @DPTR,A
  03F4  44 33     ORL A,#33h
  03F6  F0        MOVX @DPTR,A
  03F7  44 3F     ORL A,#3Fh
  03F9  F0        MOVX @DPTR,A
  03FA  A2 19     MOV C,23h.1
  03FC  92 E6     MOV ACC.6,C
  03FE  44 BF     ORL A,#BFh
  0400  F0        MOVX @DPTR,A
  0401  90 FF 9F  MOV DPTR,#FF9Fh  ; SCR
  0404  74 33     MOV A,#33h
  0406  F0        MOVX @DPTR,A
  0407  78 02     MOV R0,#02h

loc_0409:    ; xref 040D
  0409  79 EE     MOV R1,#EEh

loc_040B:    ; xref 040B
  040B  D9 FE     DJNZ R1,loc_040B
  040D  D8 FA     DJNZ R0,loc_0409
  040F  54 23     ANL A,#23h
  0411  F0        MOVX @DPTR,A
  0412  54 01     ANL A,#01h
  0414  F0        MOVX @DPTR,A
  0415  E4        CLR A
  0416  F0        MOVX @DPTR,A
  0417  90 FF CC  MOV DPTR,#FFCCh  ; UDCR
  041A  74 06     MOV A,#06h
  041C  F0        MOVX @DPTR,A
  041D  90 FF 87  MOV DPTR,#FF87h  ; ASR
  0420  E0        MOVX A,@DPTR
  0421  30 18 02  JNB 23h.0,loc_0426
  0424  B2 E7     CPL ACC.7

loc_0426:    ; xref 0421
  0426  30 E7 14  JNB ACC.7,loc_043D
  0429  90 FF CC  MOV DPTR,#FFCCh  ; UDCR
  042C  74 26     MOV A,#26h
  042E  F0        MOVX @DPTR,A
  042F  78 04     MOV R0,#04h

loc_0431:    ; xref 0435
  0431  79 EE     MOV R1,#EEh

loc_0433:    ; xref 0433
  0433  D9 FE     DJNZ R1,loc_0433
  0435  D8 FA     DJNZ R0,loc_0431
  0437  90 FF CC  MOV DPTR,#FFCCh  ; UDCR
  043A  74 06     MOV A,#06h
  043C  F0        MOVX @DPTR,A

loc_043D:    ; xref 0426
  043D  90 FF CC  MOV DPTR,#FFCCh  ; UDCR
  0440  E0        MOVX A,@DPTR
  0441  D2 E2     SETB ACC.2
  0443  F0        MOVX @DPTR,A
  0444  22        RET

sub_0445:    ; xref 0083, 00C6
  0445  C2 8C     CLR TCON.4
  0447  75 8C 44  MOV TH0,#44h
  044A  75 8A 80  MOV TL0,#80h
  044D  D2 A9     SETB IE.1
  044F  D2 8C     SETB TCON.4
  0451  22        RET

loc_0452:    ; xref 06E2
  0452  B4 61 03  CJNE A,#61h,loc_0458
  0455  02 05 1B  LJMP loc_051B

loc_0458:    ; xref 0452
  0458  B4 62 03  CJNE A,#62h,loc_045E
  045B  02 05 4B  LJMP loc_054B

loc_045E:    ; xref 0458
  045E  B4 64 03  CJNE A,#64h,loc_0464
  0461  02 05 78  LJMP loc_0578

loc_0464:    ; xref 045E
  0464  B4 66 03  CJNE A,#66h,loc_046A
  0467  02 05 87  LJMP loc_0587

loc_046A:    ; xref 0464
  046A  B4 6E 03  CJNE A,#6Eh,loc_0470
  046D  02 05 B5  LJMP loc_05B5

loc_0470:    ; xref 046A
  0470  B4 6F 03  CJNE A,#6Fh,loc_0476
  0473  02 05 DD  LJMP loc_05DD

loc_0476:    ; xref 0470
  0476  B4 70 03  CJNE A,#70h,loc_047C
  0479  02 06 11  LJMP loc_0611

loc_047C:    ; xref 0476
  047C  B4 68 03  CJNE A,#68h,loc_0482
  047F  02 06 1D  LJMP loc_061D

loc_0482:    ; xref 047C
  0482  B4 69 03  CJNE A,#69h,loc_0488
  0485  02 06 34  LJMP loc_0634

loc_0488:    ; xref 0482
  0488  B4 6A 03  CJNE A,#6Ah,loc_048E
  048B  02 06 49  LJMP loc_0649

loc_048E:    ; xref 0488
  048E  B4 6B 03  CJNE A,#6Bh,loc_0494
  0491  02 06 62  LJMP loc_0662

loc_0494:    ; xref 048E
  0494  B4 6C 03  CJNE A,#6Ch,loc_049A
  0497  02 06 71  LJMP loc_0671

loc_049A:    ; xref 0494
  049A  02 06 7A  LJMP loc_067A

loc_049D:    ; xref 0719
  049D  B4 61 03  CJNE A,#61h,loc_04A3
  04A0  02 05 1C  LJMP loc_051C

loc_04A3:    ; xref 049D
  04A3  B4 62 03  CJNE A,#62h,loc_04A9
  04A6  02 05 4C  LJMP loc_054C

loc_04A9:    ; xref 04A3
  04A9  B4 64 03  CJNE A,#64h,loc_04AF
  04AC  02 05 79  LJMP loc_0579

loc_04AF:    ; xref 04A9
  04AF  B4 66 03  CJNE A,#66h,loc_04B5
  04B2  02 05 8E  LJMP loc_058E

loc_04B5:    ; xref 04AF
  04B5  B4 6E 03  CJNE A,#6Eh,loc_04BB
  04B8  02 05 B6  LJMP loc_05B6

loc_04BB:    ; xref 04B5
  04BB  B4 6F 03  CJNE A,#6Fh,loc_04C1
  04BE  02 05 DE  LJMP loc_05DE

loc_04C1:    ; xref 04BB
  04C1  B4 70 03  CJNE A,#70h,loc_04C7
  04C4  02 06 15  LJMP loc_0615

loc_04C7:    ; xref 04C1
  04C7  B4 68 03  CJNE A,#68h,loc_04CD
  04CA  02 06 1E  LJMP loc_061E

loc_04CD:    ; xref 04C7
  04CD  B4 69 03  CJNE A,#69h,loc_04D3
  04D0  02 06 35  LJMP loc_0635

loc_04D3:    ; xref 04CD
  04D3  B4 6A 03  CJNE A,#6Ah,loc_04D9
  04D6  02 06 4A  LJMP loc_064A

loc_04D9:    ; xref 04D3
  04D9  B4 6B 03  CJNE A,#6Bh,loc_04DF
  04DC  02 06 63  LJMP loc_0663

loc_04DF:    ; xref 04D9
  04DF  B4 6C 03  CJNE A,#6Ch,loc_04E5
  04E2  02 06 72  LJMP loc_0672

loc_04E5:    ; xref 04DF
  04E5  02 06 7B  LJMP loc_067B

loc_04E8:    ; xref 073F
  04E8  E5 6B     MOV A,6Bh
  04EA  B4 00 09  CJNE A,#00h,loc_04F6
  04ED  AE 6C     MOV R6,6Ch
  04EF  7F 00     MOV R7,#00h
  04F1  12 02 91  LCALL sub_0291
  04F4  80 15     SJMP loc_050B

loc_04F6:    ; xref 04EA
  04F6  B4 01 09  CJNE A,#01h,loc_0502
  04F9  AE 6D     MOV R6,6Dh
  04FB  7F 00     MOV R7,#00h
  04FD  12 02 91  LCALL sub_0291
  0500  80 09     SJMP loc_050B

loc_0502:    ; xref 04F6
  0502  AE 6E     MOV R6,6Eh
  0504  7F 00     MOV R7,#00h
  0506  12 02 91  LCALL sub_0291
  0509  80 00     SJMP loc_050B

loc_050B:    ; xref 04F4, 0500, 0509
  050B  75 68 61  MOV 68h,#61h
  050E  75 69 61  MOV 69h,#61h
  0511  75 70 02  MOV 70h,#02h
  0514  75 71 00  MOV 71h,#00h
  0517  12 02 EE  LCALL sub_02EE
  051A  22        RET

loc_051B:    ; xref 0455
  051B  22        RET

loc_051C:    ; xref 04A0
  051C  75 69 61  MOV 69h,#61h
  051F  22        RET

loc_0520:    ; xref 0745
  0520  E5 6B     MOV A,6Bh
  0522  B4 00 12  CJNE A,#00h,loc_0537
  0525  75 6C 00  MOV 6Ch,#00h
  0528  90 FF BA  MOV DPTR,#FFBAh  ; URVLB
  052B  E0        MOVX A,@DPTR
  052C  B4 01 02  CJNE A,#01h,loc_0531
  052F  80 13     SJMP loc_0544

loc_0531:    ; xref 052C
  0531  75 68 62  MOV 68h,#62h
  0534  02 07 CE  LJMP loc_07CE

loc_0537:    ; xref 0522
  0537  B4 01 05  CJNE A,#01h,loc_053F
  053A  75 6D 00  MOV 6Dh,#00h
  053D  80 05     SJMP loc_0544

loc_053F:    ; xref 0537
  053F  75 6E 00  MOV 6Eh,#00h
  0542  80 00     SJMP loc_0544

loc_0544:    ; xref 052F, 053D, 0542
  0544  75 68 62  MOV 68h,#62h
  0547  12 02 EB  LCALL sub_02EB
  054A  22        RET

loc_054B:    ; xref 045B
  054B  22        RET

loc_054C:    ; xref 04A6
  054C  22        RET

loc_054D:    ; xref 074B
  054D  E5 6B     MOV A,6Bh
  054F  B4 00 12  CJNE A,#00h,loc_0564
  0552  75 6C 02  MOV 6Ch,#02h
  0555  90 FF BA  MOV DPTR,#FFBAh  ; URVLB
  0558  E0        MOVX A,@DPTR
  0559  B4 01 02  CJNE A,#01h,loc_055E
  055C  80 13     SJMP loc_0571

loc_055E:    ; xref 0559
  055E  75 68 64  MOV 68h,#64h
  0561  02 07 CE  LJMP loc_07CE

loc_0564:    ; xref 054F
  0564  B4 01 05  CJNE A,#01h,loc_056C
  0567  75 6D 00  MOV 6Dh,#00h
  056A  80 05     SJMP loc_0571

loc_056C:    ; xref 0564
  056C  75 6E 01  MOV 6Eh,#01h
  056F  80 00     SJMP loc_0571

loc_0571:    ; xref 055C, 056A, 056F
  0571  75 68 64  MOV 68h,#64h
  0574  12 02 EB  LCALL sub_02EB
  0577  22        RET

loc_0578:    ; xref 0461
  0578  22        RET

loc_0579:    ; xref 04AC
  0579  22        RET

loc_057A:    ; xref 0751
  057A  90 FF BA  MOV DPTR,#FFBAh  ; URVLB
  057D  E0        MOVX A,@DPTR
  057E  F5 6A     MOV 6Ah,A
  0580  75 68 66  MOV 68h,#66h
  0583  12 02 EB  LCALL sub_02EB
  0586  22        RET

loc_0587:    ; xref 0467
  0587  E5 6A     MOV A,6Ah
  0589  90 FF CB  MOV DPTR,#FFCBh  ; UDAR
  058C  F0        MOVX @DPTR,A
  058D  22        RET

loc_058E:    ; xref 04B2
  058E  22        RET

loc_058F:    ; xref 075E
  058F  75 F0 12  MOV B,#12h
  0592  90 FF BF  MOV DPTR,#FFBFh  ; URLHB
  0595  E0        MOVX A,@DPTR
  0596  70 09     JNZ loc_05A1
  0598  90 FF BE  MOV DPTR,#FFBEh  ; URLLB
  059B  E0        MOVX A,@DPTR
  059C  B5 F0 00  CJNE A,B,loc_059F

loc_059F:    ; xref 059C
  059F  40 02     JC loc_05A3

loc_05A1:    ; xref 0596
  05A1  E5 F0     MOV A,B

loc_05A3:    ; xref 059F, 070F
  05A3  F5 70     MOV 70h,A
  05A5  75 71 80  MOV 71h,#80h
  05A8  75 68 6E  MOV 68h,#6Eh
  05AB  75 69 6E  MOV 69h,#6Eh
  05AE  12 01 1C  LCALL sub_011C
  05B1  12 02 EE  LCALL sub_02EE
  05B4  22        RET

loc_05B5:    ; xref 046D
  05B5  22        RET

loc_05B6:    ; xref 04B8
  05B6  75 69 6E  MOV 69h,#6Eh
  05B9  22        RET

loc_05BA:    ; xref 0764
  05BA  75 F0 20  MOV B,#20h
  05BD  90 FF BF  MOV DPTR,#FFBFh  ; URLHB
  05C0  E0        MOVX A,@DPTR
  05C1  70 09     JNZ loc_05CC
  05C3  90 FF BE  MOV DPTR,#FFBEh  ; URLLB
  05C6  E0        MOVX A,@DPTR
  05C7  B5 F0 00  CJNE A,B,loc_05CA

loc_05CA:    ; xref 05C7
  05CA  40 02     JC loc_05CE

loc_05CC:    ; xref 05C1
  05CC  E5 F0     MOV A,B

loc_05CE:    ; xref 05CA
  05CE  F5 70     MOV 70h,A
  05D0  75 71 92  MOV 71h,#92h
  05D3  75 68 6F  MOV 68h,#6Fh
  05D6  75 69 6F  MOV 69h,#6Fh
  05D9  12 02 EE  LCALL sub_02EE
  05DC  22        RET

loc_05DD:    ; xref 0473
  05DD  22        RET

loc_05DE:    ; xref 04BE
  05DE  75 69 6F  MOV 69h,#6Fh
  05E1  22        RET

loc_05E2:    ; xref 076A
  05E2  90 FF BA  MOV DPTR,#FFBAh  ; URVLB
  05E5  E0        MOVX A,@DPTR
  05E6  B4 00 08  CJNE A,#00h,loc_05F1
  05E9  75 71 B2  MOV 71h,#B2h
  05EC  75 F0 04  MOV B,#04h
  05EF  80 06     SJMP loc_05F7

loc_05F1:    ; xref 05E6
  05F1  75 71 B6  MOV 71h,#B6h
  05F4  75 F0 26  MOV B,#26h

loc_05F7:    ; xref 05EF
  05F7  90 FF BF  MOV DPTR,#FFBFh  ; URLHB
  05FA  E0        MOVX A,@DPTR
  05FB  70 09     JNZ loc_0606
  05FD  90 FF BE  MOV DPTR,#FFBEh  ; URLLB
  0600  E0        MOVX A,@DPTR
  0601  B5 F0 00  CJNE A,B,loc_0604

loc_0604:    ; xref 0601
  0604  40 02     JC loc_0608

loc_0606:    ; xref 05FB
  0606  E5 F0     MOV A,B

loc_0608:    ; xref 0604
  0608  F5 70     MOV 70h,A
  060A  75 68 70  MOV 68h,#70h
  060D  12 02 EE  LCALL sub_02EE
  0610  22        RET

loc_0611:    ; xref 0479
  0611  75 69 70  MOV 69h,#70h
  0614  22        RET

loc_0615:    ; xref 04C4
  0615  22        RET

loc_0616:    ; xref 0773
  0616  75 68 68  MOV 68h,#68h
  0619  12 02 EB  LCALL sub_02EB
  061C  22        RET

loc_061D:    ; xref 047F
  061D  22        RET

loc_061E:    ; xref 04CA
  061E  22        RET

loc_061F:    ; xref 0779
  061F  AE 6F     MOV R6,6Fh
  0621  12 02 91  LCALL sub_0291
  0624  75 68 69  MOV 68h,#69h
  0627  75 69 69  MOV 69h,#69h
  062A  75 70 01  MOV 70h,#01h
  062D  75 71 00  MOV 71h,#00h
  0630  12 02 EE  LCALL sub_02EE
  0633  22        RET

loc_0634:    ; xref 0485
  0634  22        RET

loc_0635:    ; xref 04D0
  0635  75 69 69  MOV 69h,#69h
  0638  22        RET

loc_0639:    ; xref 077F
  0639  90 FF BA  MOV DPTR,#FFBAh  ; URVLB
  063C  E0        MOVX A,@DPTR
  063D  F5 6F     MOV 6Fh,A
  063F  75 6E 01  MOV 6Eh,#01h
  0642  75 68 6A  MOV 68h,#6Ah
  0645  12 02 EB  LCALL sub_02EB
  0648  22        RET

loc_0649:    ; xref 048B
  0649  22        RET

loc_064A:    ; xref 04D6
  064A  22        RET

loc_064B:    ; xref 0785
  064B  AE 6D     MOV R6,6Dh
  064D  7F 00     MOV R7,#00h
  064F  12 02 91  LCALL sub_0291
  0652  75 68 6B  MOV 68h,#6Bh
  0655  75 69 6B  MOV 69h,#6Bh
  0658  75 70 01  MOV 70h,#01h
  065B  75 71 00  MOV 71h,#00h
  065E  12 02 EE  LCALL sub_02EE
  0661  22        RET

loc_0662:    ; xref 0491
  0662  22        RET

loc_0663:    ; xref 04DC
  0663  75 69 6B  MOV 69h,#6Bh
  0666  22        RET

loc_0667:    ; xref 078B
  0667  75 6E 01  MOV 6Eh,#01h
  066A  75 68 6C  MOV 68h,#6Ch
  066D  12 02 EB  LCALL sub_02EB
  0670  22        RET

loc_0671:    ; xref 0497
  0671  22        RET

loc_0672:    ; xref 04E2
  0672  22        RET

loc_0673:    ; xref 078E
  0673  75 68 6D  MOV 68h,#6Dh
  0676  12 02 EB  LCALL sub_02EB
  0679  22        RET

loc_067A:    ; xref 049A
  067A  22        RET

loc_067B:    ; xref 04E5
  067B  22        RET

sub_067C:    ; xref 009B
  067C  90 FF AC  MOV DPTR,#FFACh  ; UIS1R
  067F  E0        MOVX A,@DPTR
  0680  F5 F0     MOV B,A
  0682  90 FF AF  MOV DPTR,#FFAFh  ; UIE1R
  0685  E0        MOVX A,@DPTR
  0686  55 F0     ANL A,B
  0688  20 E0 1F  JB ACC.0,loc_06AA
  068B  20 E1 26  JB ACC.1,loc_06B4
  068E  90 FF AB  MOV DPTR,#FFABh  ; UIS2R
  0691  E0        MOVX A,@DPTR
  0692  F5 F0     MOV B,A
  0694  90 FF AE  MOV DPTR,#FFAEh  ; UIE2R
  0697  E0        MOVX A,@DPTR
  0698  55 F0     ANL A,B
  069A  20 E2 21  JB ACC.2,loc_06BE
  069D  20 E4 2D  JB ACC.4,loc_06CD
  06A0  E4        CLR A
  06A1  90 FF AC  MOV DPTR,#FFACh  ; UIS1R
  06A4  F0        MOVX @DPTR,A
  06A5  90 FF AB  MOV DPTR,#FFABh  ; UIS2R
  06A8  F0        MOVX @DPTR,A
  06A9  22        RET

loc_06AA:    ; xref 0688
  06AA  74 FE     MOV A,#FEh
  06AC  90 FF AC  MOV DPTR,#FFACh  ; UIS1R
  06AF  F0        MOVX @DPTR,A
  06B0  12 06 D4  LCALL sub_06D4
  06B3  22        RET

loc_06B4:    ; xref 068B
  06B4  74 FD     MOV A,#FDh
  06B6  90 FF AC  MOV DPTR,#FFACh  ; UIS1R
  06B9  F0        MOVX @DPTR,A
  06BA  12 06 EA  LCALL sub_06EA
  06BD  22        RET

loc_06BE:    ; xref 069A
  06BE  74 FB     MOV A,#FBh
  06C0  90 FF AB  MOV DPTR,#FFABh  ; UIS2R
  06C3  F0        MOVX @DPTR,A
  06C4  90 FF CB  MOV DPTR,#FFCBh  ; UDAR
  06C7  E0        MOVX A,@DPTR
  06C8  60 02     JZ loc_06CC
  06CA  71 BC     ACALL sub_03BC

loc_06CC:    ; xref 06C8
  06CC  22        RET

loc_06CD:    ; xref 069D
  06CD  74 EF     MOV A,#EFh
  06CF  90 FF AB  MOV DPTR,#FFABh  ; UIS2R
  06D2  F0        MOVX @DPTR,A
  06D3  22        RET

sub_06D4:    ; xref 06B0
  06D4  E5 68     MOV A,68h
  06D6  F5 F0     MOV B,A
  06D8  75 68 00  MOV 68h,#00h
  06DB  54 E0     ANL A,#E0h
  06DD  B4 60 05  CJNE A,#60h,loc_06E5
  06E0  E5 F0     MOV A,B
  06E2  02 04 52  LJMP loc_0452

loc_06E5:    ; xref 06DD
  06E5  E5 F0     MOV A,B
  06E7  02 01 8C  LJMP loc_018C

sub_06EA:    ; xref 06BA
  06EA  90 FF C0  MOV DPTR,#FFC0h  ; UEIR
  06ED  74 00     MOV A,#00h
  06EF  F0        MOVX @DPTR,A
  06F0  90 FF CA  MOV DPTR,#FFCAh  ; UERSR
  06F3  E0        MOVX A,@DPTR
  06F4  30 E6 03  JNB ACC.6,loc_06FA
  06F7  02 07 21  LJMP loc_0721

loc_06FA:    ; xref 06F4
  06FA  E5 69     MOV A,69h
  06FC  F5 F0     MOV B,A
  06FE  75 69 00  MOV 69h,#00h
  0701  70 0F     JNZ loc_0712
  0703  90 FF C9  MOV DPTR,#FFC9h  ; UETSR
  0706  E0        MOVX A,@DPTR
  0707  44 88     ORL A,#88h
  0709  F0        MOVX @DPTR,A
  070A  C2 E3     CLR ACC.3
  070C  F0        MOVX @DPTR,A
  070D  74 12     MOV A,#12h
  070F  02 05 A3  LJMP loc_05A3

loc_0712:    ; xref 0701
  0712  54 E0     ANL A,#E0h
  0714  B4 60 05  CJNE A,#60h,loc_071C
  0717  E5 F0     MOV A,B
  0719  02 04 9D  LJMP loc_049D

loc_071C:    ; xref 0714
  071C  E5 F0     MOV A,B
  071E  02 01 B9  LJMP loc_01B9

loc_0721:    ; xref 06F7
  0721  90 FF B8  MOV DPTR,#FFB8h  ; URT
  0724  E0        MOVX A,@DPTR
  0725  F5 F0     MOV B,A
  0727  54 1F     ANL A,#1Fh
  0729  F5 6B     MOV 6Bh,A
  072B  E5 F0     MOV A,B
  072D  54 60     ANL A,#60h
  072F  B4 00 03  CJNE A,#00h,loc_0735
  0732  02 07 38  LJMP loc_0738

loc_0735:    ; xref 072F
  0735  02 07 91  LJMP loc_0791

loc_0738:    ; xref 0732
  0738  90 FF B9  MOV DPTR,#FFB9h  ; URC
  073B  E0        MOVX A,@DPTR
  073C  B4 00 03  CJNE A,#00h,loc_0742
  073F  02 04 E8  LJMP loc_04E8

loc_0742:    ; xref 073C
  0742  B4 01 03  CJNE A,#01h,loc_0748
  0745  02 05 20  LJMP loc_0520

loc_0748:    ; xref 0742
  0748  B4 03 03  CJNE A,#03h,loc_074E
  074B  02 05 4D  LJMP loc_054D

loc_074E:    ; xref 0748
  074E  B4 05 03  CJNE A,#05h,loc_0754
  0751  02 05 7A  LJMP loc_057A

loc_0754:    ; xref 074E
  0754  B4 06 19  CJNE A,#06h,loc_0770
  0757  90 FF BB  MOV DPTR,#FFBBh  ; URVHB
  075A  E0        MOVX A,@DPTR
  075B  B4 01 03  CJNE A,#01h,loc_0761
  075E  02 05 8F  LJMP loc_058F

loc_0761:    ; xref 075B
  0761  B4 02 03  CJNE A,#02h,loc_0767
  0764  02 05 BA  LJMP loc_05BA

loc_0767:    ; xref 0761
  0767  B4 03 03  CJNE A,#03h,loc_076D
  076A  02 05 E2  LJMP loc_05E2

loc_076D:    ; xref 0767
  076D  02 07 CE  LJMP loc_07CE

loc_0770:    ; xref 0754
  0770  B4 07 03  CJNE A,#07h,loc_0776
  0773  02 06 16  LJMP loc_0616

loc_0776:    ; xref 0770
  0776  B4 08 03  CJNE A,#08h,loc_077C
  0779  02 06 1F  LJMP loc_061F

loc_077C:    ; xref 0776
  077C  B4 09 03  CJNE A,#09h,loc_0782
  077F  02 06 39  LJMP loc_0639

loc_0782:    ; xref 077C
  0782  B4 0A 03  CJNE A,#0Ah,loc_0788
  0785  02 06 4B  LJMP loc_064B

loc_0788:    ; xref 0782
  0788  B4 0B 03  CJNE A,#0Bh,loc_078E
  078B  02 06 67  LJMP loc_0667

loc_078E:    ; xref 0788
  078E  02 06 73  LJMP loc_0673

loc_0791:    ; xref 0735
  0791  90 FF BA  MOV DPTR,#FFBAh  ; URVLB
  0794  E0        MOVX A,@DPTR
  0795  B4 09 03  CJNE A,#09h,loc_079B
  0798  02 01 E6  LJMP loc_01E6

loc_079B:    ; xref 0795
  079B  B4 0A 03  CJNE A,#0Ah,loc_07A1
  079E  02 01 F5  LJMP loc_01F5

loc_07A1:    ; xref 079B
  07A1  B4 0B 03  CJNE A,#0Bh,loc_07A7
  07A4  02 02 0B  LJMP loc_020B

loc_07A7:    ; xref 07A1
  07A7  B4 0C 03  CJNE A,#0Ch,loc_07AD
  07AA  02 02 1A  LJMP loc_021A

loc_07AD:    ; xref 07A7
  07AD  B4 0D 03  CJNE A,#0Dh,loc_07B3
  07B0  02 02 0B  LJMP loc_020B

loc_07B3:    ; xref 07AD
  07B3  B4 0C 03  CJNE A,#0Ch,loc_07B9
  07B6  02 02 1A  LJMP loc_021A

loc_07B9:    ; xref 07B3
  07B9  B4 10 03  CJNE A,#10h,loc_07BF
  07BC  02 02 29  LJMP loc_0229

loc_07BF:    ; xref 07B9
  07BF  B4 11 03  CJNE A,#11h,loc_07C5
  07C2  02 02 43  LJMP loc_0243

loc_07C5:    ; xref 07BF
  07C5  B4 12 03  CJNE A,#12h,loc_07CB
  07C8  02 02 59  LJMP loc_0259

loc_07CB:    ; xref 07C5
  07CB  02 02 6B  LJMP loc_026B

loc_07CE:    ; xref 0534, 0561, 076D
  07CE  90 FF C0  MOV DPTR,#FFC0h  ; UEIR
  07D1  74 00     MOV A,#00h
  07D3  F0        MOVX @DPTR,A
  07D4  90 FF C8  MOV DPTR,#FFC8h  ; UECR
  07D7  74 6D     MOV A,#6Dh
  07D9  F0        MOVX @DPTR,A
  07DA  90 FF A9  MOV DPTR,#FFA9h  ; EDCR
  07DD  74 E2     MOV A,#E2h
  07DF  F0        MOVX @DPTR,A
  07E0  90 FF C0  MOV DPTR,#FFC0h  ; UEIR
  07E3  74 00     MOV A,#00h
  07E5  F0        MOVX @DPTR,A
  07E6  90 FF CA  MOV DPTR,#FFCAh  ; UERSR
  07E9  E0        MOVX A,@DPTR
  07EA  C2 E6     CLR ACC.6
  07EC  F0        MOVX @DPTR,A
  07ED  22        RET
  07EE  DB FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh,FFh   ; data/unreached
  07FE  DB 68h,16h   ; data/unreached

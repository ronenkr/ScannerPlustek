/*
 * GT6816 stage-1 RAM execution probe.
 *
 * The program is intentionally independent of the scanner firmware.  It
 * leaves a marker in the documented internal USB transmit registers,
 * configures DMA3 to read those registers through USB, and then services the
 * watchdog.  All addresses below are GT6816 special-function registers
 * documented by the chip datasheet.
 */
#include <stdint.h>

#define GT_REG8(address) (*(volatile __xdata uint8_t *)(address))

#define DMA3_CONTROL       0xFFA9u
#define DMA3_AUTORELOAD    0xFFB2u
#define DMA3_BYTE_COUNT8   0xFFC2u
#define DMA3_BANKED_CTRL2  0xFFC3u
#define USB_DSTR0          0xFFD0u
#define USB_BANK_SELECT    0xFFB0u
#define WATCHDOG           0xFF96u

#define MARKER_SIZE 8u

void main(void)
{
    uint8_t i;

    /* DSTR0..DSTR7 are the documented internal 8-byte USB TX registers. */
    for (i = 0; i < MARKER_SIZE; ++i) {
        GT_REG8(USB_DSTR0 + i) = (uint8_t)(0xA5u ^ i);
    }

    /*
     * FFC3 is bank 1B. Enable requests from the internal 8-byte registers,
     * preserving all other bank-select and control bits. FFC0 is read-only
     * and the endpoint control reset enables EP1 IN (TE/TOE both set).
     */
    {
        uint8_t bank = GT_REG8(USB_BANK_SELECT);
        GT_REG8(USB_BANK_SELECT) = (uint8_t)(bank | 0x80u);
        GT_REG8(DMA3_BANKED_CTRL2) = 0x20u;
        GT_REG8(USB_BANK_SELECT) = bank;
    }

    /* One 8-byte packet from DSTR0..DSTR7; FFA9 bit 4 selects that source. */
    GT_REG8(DMA3_AUTORELOAD) = 0x00u;
    GT_REG8(DMA3_BYTE_COUNT8) = MARKER_SIZE;
    /* Preserve reset timing bits 7:5; bit 4 internal, bit 1 load, USB read. */
    GT_REG8(DMA3_CONTROL) = 0xF2u;

    for (;;) {
        /* GT6816 watchdog feed sequence. */
        GT_REG8(WATCHDOG) = 0x68u;
        GT_REG8(WATCHDOG) = 0x01u;
    }
}

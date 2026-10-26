/*
 * GT6816 zero-destination SROM reload probe.
 *
 * This image sends the standard A5^index eight-byte EP1 marker, waits for
 * EP1 TX completion, then asks the controller to re-download external SROM
 * code into M1 address zero. It never writes the external EEPROM.
 */
#include <stdint.h>

#define GT_REG8(address) (*(volatile __xdata uint8_t *)(address))

#define DMA_CONTROL       0xFF80u
#define DMA1_START_HI     0xFF83u
#define DMA1_START_LO     0xFF84u
#define USB_BANK_SELECT   0xFFB0u
#define DMA3_AUTORELOAD   0xFFB2u
#define USB_INT_STATUS    0xFFACu
#define DMA3_BYTE_COUNT8  0xFFC2u
#define DMA3_BANKED_CTRL2 0xFFC3u
#define DMA3_CONTROL      0xFFA9u
#define WATCHDOG          0xFF96u
#define USB_DSTR0         0xFFD0u

#define MARKER_SIZE 8u

static void feed_watchdog(void)
{
    GT_REG8(WATCHDOG) = 0x68u;
    GT_REG8(WATCHDOG) = 0x01u;
}

static void arm_marker_dma(void)
{
    uint8_t bank;

    /* FFC3 bit 5 enables internal DSTR requests; preserve FFB0 bits 6:0. */
    bank = GT_REG8(USB_BANK_SELECT);
    GT_REG8(USB_BANK_SELECT) = (uint8_t)(bank | 0x80u);
    GT_REG8(DMA3_BANKED_CTRL2) = 0x20u;
    GT_REG8(USB_BANK_SELECT) = bank;

    GT_REG8(DMA3_AUTORELOAD) = 0x00u;
    GT_REG8(DMA3_BYTE_COUNT8) = MARKER_SIZE;
    /* FFAC is bank 1A; force bit 7 low while preserving bits 6:0. */
    GT_REG8(USB_BANK_SELECT) = (uint8_t)(GT_REG8(USB_BANK_SELECT) & 0x7Fu);
    GT_REG8(USB_INT_STATUS) = (uint8_t)(GT_REG8(USB_INT_STATUS) & (uint8_t)~0x04u);
    /* timing=111, internal DSTR source, USB read, load=1 */
    GT_REG8(DMA3_CONTROL) = 0xF2u;
}

static void wait_ep1_done(void)
{
    for (;;) {
        GT_REG8(USB_BANK_SELECT) = (uint8_t)(GT_REG8(USB_BANK_SELECT) & 0x7Fu);
        if ((GT_REG8(USB_INT_STATUS) & 0x04u) != 0u) {
            return;
        }
        feed_watchdog();
    }
}

static void request_srom_at_zero(void)
{
    GT_REG8(DMA1_START_HI) = 0x00u;
    GT_REG8(DMA1_START_LO) = 0x00u;
    GT_REG8(DMA_CONTROL) = 0x08u;
    for (;;) {
        feed_watchdog();
    }
}

void main(void)
{
    uint8_t i;

    for (i = 0; i < MARKER_SIZE; ++i) {
        GT_REG8(USB_DSTR0 + i) = (uint8_t)(0xA5u ^ i);
    }
    arm_marker_dma();
    wait_ep1_done();
    request_srom_at_zero();
}

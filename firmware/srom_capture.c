/*
 * GT6816 SROM reload diagnostic.
 *
 * On its first invocation the reset image checks a host-installed sentinel
 * at M1 1000h, points DMA1 there, and requests the documented external SROM
 * re-download.  After reset, the image at M1 address zero sees a changed
 * sentinel and streams 2048 code bytes through the documented internal USB
 * transmit registers.  This never writes the EEPROM.
 */
#include <stdint.h>

#define GT_REG8(address) (*(volatile __xdata uint8_t *)(address))
#define GT_CODE8(address) (*(const __code uint8_t *)(address))

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

#define CAPTURE_START 0x1000u
#define CAPTURE_SIZE  2048u
#define CHUNK_SIZE    8u
#define PRE_MARKER    0xC3u
#define POST_MARKER   0x3Cu

static uint8_t sentinel_byte(uint16_t offset)
{
    return (uint8_t)(0x5Au ^ (uint8_t)(offset * 3u));
}

static uint8_t capture_changed(void)
{
    uint8_t i;
    for (i = 0; i < CHUNK_SIZE; ++i) {
        if (GT_CODE8(CAPTURE_START + i) != sentinel_byte(i)) {
            return 1u;
        }
    }
    return 0u;
}

static void feed_watchdog(void)
{
    GT_REG8(WATCHDOG) = 0x68u;
    GT_REG8(WATCHDOG) = 0x01u;
}

static void arm_ep1_registers(void);
static void wait_ep1_done(void);

static void request_srom_reload(void)
{
    uint8_t i;

    /* This marker proves the pre-reload image reached EP1 and is waiting. */
    for (i = 0; i < CHUNK_SIZE; ++i) {
        GT_REG8(USB_DSTR0 + i) = (uint8_t)(PRE_MARKER + i);
    }
    arm_ep1_registers();
    wait_ep1_done();

    /* DMA1 destination M1 = 1000h; source is the external SROM downloader. */
    GT_REG8(DMA1_START_HI) = 0x10u;
    GT_REG8(DMA1_START_LO) = 0x00u;
    GT_REG8(DMA_CONTROL) = 0x08u;
    for (;;) {
        feed_watchdog();
    }
}

static void arm_ep1_registers(void)
{
    uint8_t bank;

    /* FFC3 bit 5 enables the internal DSTR request; preserve FFB0. */
    bank = GT_REG8(USB_BANK_SELECT);
    GT_REG8(USB_BANK_SELECT) = (uint8_t)(bank | 0x80u);
    GT_REG8(DMA3_BANKED_CTRL2) = 0x20u;
    GT_REG8(USB_BANK_SELECT) = bank;

    GT_REG8(DMA3_AUTORELOAD) = 0x00u;
    GT_REG8(DMA3_BYTE_COUNT8) = CHUNK_SIZE;
    /* FFAC is bank 1A; preserve FFB0 bits 6:0 while forcing bit 7 low. */
    GT_REG8(USB_BANK_SELECT) = (uint8_t)(GT_REG8(USB_BANK_SELECT) & 0x7Fu);
    /* Clear EP1 TX-done while preserving the other status bits. */
    GT_REG8(USB_INT_STATUS) = (uint8_t)(GT_REG8(USB_INT_STATUS) & (uint8_t)~0x04u);
    /* timing=111, internal DSTR source, USB read, load=1 */
    GT_REG8(DMA3_CONTROL) = 0xF2u;
}

static void wait_ep1_done(void)
{
    for (;;) {
        /* Keep every FFAC poll on bank 1A. */
        GT_REG8(USB_BANK_SELECT) = (uint8_t)(GT_REG8(USB_BANK_SELECT) & 0x7Fu);
        if ((GT_REG8(USB_INT_STATUS) & 0x04u) != 0u) {
            return;
        }
        feed_watchdog();
    }
}

static void arm_ep1_chunk(const __code uint8_t *source)
{
    uint8_t i;

    for (i = 0; i < CHUNK_SIZE; ++i) {
        GT_REG8(USB_DSTR0 + i) = source[i];
    }
    arm_ep1_registers();
}

static void stream_capture(void)
{
    uint16_t offset;
    uint8_t i;

    /* Distinct marker proves the post-reload image reached EP1. */
    for (i = 0; i < CHUNK_SIZE; ++i) {
        GT_REG8(USB_DSTR0 + i) = (uint8_t)(POST_MARKER + i);
    }
    arm_ep1_registers();
    wait_ep1_done();

    for (offset = 0; offset < CAPTURE_SIZE; offset += CHUNK_SIZE) {
        arm_ep1_chunk((const __code uint8_t *)(CAPTURE_START + offset));
        wait_ep1_done();
    }
    for (;;) {
        feed_watchdog();
    }
}

void main(void)
{
    if (capture_changed() == 0u) {
        request_srom_reload();
    }
    stream_capture();
}

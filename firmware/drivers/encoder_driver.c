/*******************************************************************************
 * @file    encoder_driver.c
 * @brief   Encoder driver implementation — wraps BSP encoder functions.
 ******************************************************************************/

#include "encoder_driver.h"
#include "../bsp/bsp.h"

void EncoderDriver_Init(void) {
    /* BSP_Encoder_Init already called by BSP_Init */
}

int32_t EncoderDriver_GetCount(void) {
    return BSP_Encoder_GetCount();
}

void EncoderDriver_Reset(void) {
    BSP_Encoder_Reset();
}

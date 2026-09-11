/*******************************************************************************
 * @file    encoder_driver.h
 * @brief   Encoder driver interface — abstraction over BSP encoder counter.
 ******************************************************************************/
#ifndef ENCODER_DRIVER_H
#define ENCODER_DRIVER_H

#include <stdint.h>

void EncoderDriver_Init(void);
int32_t EncoderDriver_GetCount(void);
void EncoderDriver_Reset(void);

#endif /* ENCODER_DRIVER_H */

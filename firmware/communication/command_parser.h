#ifndef COMMAND_PARSER_H
#define COMMAND_PARSER_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    CMD_NONE = 0,
    CMD_SET_RPM,
    CMD_START,
    CMD_STOP,
    CMD_RESET_FAULT,
    CMD_GET_STATUS,
    CMD_SET_GAINS
} CommandType_t;

typedef struct {
    CommandType_t type;
    union {
        float rpm;
        struct {
            float kp;
            float ki;
        } gains;
    } payload;
} ParsedCommand_t;

// Abstract interface to be implemented by a specific serialization layer (e.g., ASCII or binary)
bool CommandParser_ParseBuffer(const uint8_t* buffer, uint16_t length, ParsedCommand_t* out_cmd);

#endif

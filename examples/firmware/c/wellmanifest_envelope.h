#ifndef WELLMANIFEST_ENVELOPE_H
#define WELLMANIFEST_ENVELOPE_H

#include <stddef.h>
#include <stdint.h>

#define WM_PROTOCOL_SPEC "wellmanifest.protocol/v1"
#define WM_MAX_URI 192
#define WM_MAX_RUN_ID 160
#define WM_MAX_CONTENT_TYPE 64

// Thin firmware clients send a bounded envelope to a sidecar/server. They do
// not embed the full parser, schema engine or arbitrary code executor.
typedef enum {
    WM_SEVERITY_ERROR = 1,
    WM_SEVERITY_WARNING = 2,
    WM_SEVERITY_INFO = 3
} wm_severity_t;

typedef struct {
    char id[WM_MAX_RUN_ID + 1];
    char operation[WM_MAX_URI + 1];
    char content_type[WM_MAX_CONTENT_TYPE + 1];
    const uint8_t *payload;
    size_t payload_length;
} wm_envelope_t;

#endif

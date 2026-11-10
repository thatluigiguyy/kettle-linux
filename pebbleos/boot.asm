; =====================================================================
;  PebbleOS boot sector
;  The BIOS loads these 512 bytes to address 0x7C00 and jumps here.
;  Our only job: load the kernel from the disk into memory and jump to it.
; =====================================================================
[org 0x7C00]
[bits 16]

KERNEL_SEG     equ 0x1000      ; kernel is loaded at 0x1000:0000 = 0x10000
KERNEL_SECTORS equ 16          ; 16 sectors * 512 bytes = 8 KB kernel

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00             ; stack grows down from just below us
    sti
    mov [boot_drive], dl       ; BIOS tells us which drive we booted from

    mov si, msg_loading
    call print

    mov cx, 3                  ; floppies can be flaky: try 3 times
.retry:
    push cx
    mov ax, KERNEL_SEG
    mov es, ax
    xor bx, bx                 ; es:bx = where to put the data
    mov ah, 0x02               ; BIOS: read sectors
    mov al, KERNEL_SECTORS
    mov ch, 0                  ; cylinder 0
    mov cl, 2                  ; sector 2 (sector 1 is this boot sector)
    mov dh, 0                  ; head 0
    mov dl, [boot_drive]
    int 0x13
    pop cx
    jnc .loaded
    xor ah, ah                 ; reset the disk and try again
    mov dl, [boot_drive]
    int 0x13
    loop .retry

    mov si, msg_error
    call print
    jmp $

.loaded:
    mov dl, [boot_drive]
    jmp KERNEL_SEG:0x0000      ; hand control to the kernel!

; print a zero-terminated string at ds:si using the BIOS
print:
    lodsb
    or al, al
    jz .done
    mov ah, 0x0E
    xor bh, bh
    int 0x10
    jmp print
.done:
    ret

boot_drive  db 0
msg_loading db 'Loading PebbleOS...', 13, 10, 0
msg_error   db 'Disk read error!', 0

times 510 - ($ - $$) db 0
dw 0xAA55                      ; magic number: "this disk is bootable"

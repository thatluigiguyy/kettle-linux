; =====================================================================
;  PebbleOS kernel
;  16-bit real mode. Draws straight into video memory (0xB8000),
;  uses the BIOS for keyboard, clock and memory info.
; =====================================================================
[bits 16]
[org 0]

COLS        equ 80
ROWS        equ 25
TOP         equ 3              ; rows reserved for the title bar
MAXLEN      equ 70             ; longest command you can type
BAR_ATTR    equ 0x1F           ; white on blue
SUB_ATTR    equ 0x1B           ; cyan on blue
LINE_ATTR   equ 0x08           ; dark grey
PROMPT_ATTR equ 0x0E           ; yellow
ERROR_ATTR  equ 0x0C           ; light red

; ---------------------------------------------------------------------
start:
    cli
    mov ax, cs
    mov ds, ax
    mov es, ax
    mov ax, 0x8000             ; stack at 0x8000:FFFE (safely below 640K)
    mov ss, ax
    mov sp, 0xFFFE
    sti
    mov ax, 0xB800             ; fs -> text-mode video memory
    mov fs, ax
    cld

    mov ax, 0x0003             ; 80x25 colour text mode
    int 0x10

    call clear_screen
    mov si, msg_welcome
    call puts

main_loop:
    mov bl, PROMPT_ATTR
    mov si, str_prompt
    call puts_attr
    mov di, input_buf
    call readline
    call run_command
    jmp main_loop

; =====================================================================
;  Screen driver
; =====================================================================

; di = byte offset of the cursor in video memory
calc_off:
    push ax
    push dx
    movzx ax, byte [cur_y]
    mov dx, COLS
    mul dx
    movzx dx, byte [cur_x]
    add ax, dx
    shl ax, 1
    mov di, ax
    pop dx
    pop ax
    ret

; print the character in al (handles newline 10 and backspace 8)
putc:
    pusha
    cmp al, 10
    je .newline
    cmp al, 8
    je .backspace
    call calc_off
    mov ah, [attr]
    mov [fs:di], ax
    inc byte [cur_x]
    cmp byte [cur_x], COLS
    jb .done
.newline:
    mov byte [cur_x], 0
    inc byte [cur_y]
    cmp byte [cur_y], ROWS
    jb .done
    call scroll
    mov byte [cur_y], ROWS - 1
    jmp .done
.backspace:
    cmp byte [cur_x], 0
    je .done
    dec byte [cur_x]
    call calc_off
    mov al, ' '
    mov ah, [attr]
    mov [fs:di], ax
.done:
    call update_cursor
    popa
    ret

; print zero-terminated string at ds:si
puts:
    push ax
    push si
.loop:
    lodsb
    test al, al
    jz .done
    call putc
    jmp .loop
.done:
    pop si
    pop ax
    ret

; print string at si in colour bl, then restore the normal colour
puts_attr:
    push ax
    mov al, [attr]
    push ax
    mov [attr], bl
    call puts
    pop ax
    mov [attr], al
    pop ax
    ret

; write string si at row dh, column dl, colour bl (doesn't move the cursor)
print_at:
    pusha
    push dx
    movzx ax, dh
    mov cx, COLS
    mul cx
    pop dx
    movzx cx, dl
    add ax, cx
    shl ax, 1
    mov di, ax
    mov ah, bl
.loop:
    lodsb
    test al, al
    jz .done
    mov [fs:di], ax
    add di, 2
    jmp .loop
.done:
    popa
    ret

; move everything below the title bar up one line
scroll:
    pusha
    push ds
    push es
    mov ah, [attr]
    mov bx, 0xB800
    mov ds, bx
    mov es, bx
    mov si, (TOP + 1) * COLS * 2
    mov di, TOP * COLS * 2
    mov cx, (ROWS - TOP - 1) * COLS
    rep movsw
    mov al, ' '
    mov cx, COLS
    rep stosw                  ; blank the new bottom line
    pop es
    pop ds
    popa
    ret

update_cursor:
    pusha
    mov ah, 0x02
    xor bh, bh
    mov dh, [cur_y]
    mov dl, [cur_x]
    int 0x10
    popa
    ret

clear_screen:
    pusha
    xor di, di
    mov al, ' '
    mov ah, [attr]
    mov cx, COLS * ROWS
.loop:
    mov [fs:di], ax
    add di, 2
    loop .loop
    call draw_bar
    mov byte [cur_x], 0
    mov byte [cur_y], TOP
    call update_cursor
    popa
    ret

draw_bar:
    pusha
    xor di, di
    mov ax, (BAR_ATTR << 8) | ' '
    mov cx, COLS * 2
.blue:
    mov [fs:di], ax
    add di, 2
    loop .blue
    mov ax, (LINE_ATTR << 8) | 0xC4   ; horizontal line character
    mov cx, COLS
.line:
    mov [fs:di], ax
    add di, 2
    loop .line
    mov si, str_title
    mov dx, 0x0002             ; row 0, col 2
    mov bl, BAR_ATTR
    call print_at
    mov si, str_subtitle
    mov dx, 0x0102             ; row 1, col 2
    mov bl, SUB_ATTR
    call print_at
    popa
    ret

; print al as two BCD digits (the clock speaks BCD)
print_bcd:
    push ax
    shr al, 4
    add al, '0'
    call putc
    pop ax
    push ax
    and al, 0x0F
    add al, '0'
    call putc
    pop ax
    ret

; print ax as a decimal number
print_dec:
    pusha
    xor cx, cx
    mov bx, 10
.split:
    xor dx, dx
    div bx
    push dx
    inc cx
    test ax, ax
    jnz .split
.out:
    pop ax
    add al, '0'
    call putc
    loop .out
    popa
    ret

newline:
    push ax
    mov al, 10
    call putc
    pop ax
    ret

; =====================================================================
;  Keyboard
; =====================================================================

; read a line into ds:di (max MAXLEN chars), zero-terminated
readline:
    pusha
    xor cx, cx
.key:
    xor ah, ah
    int 0x16                   ; BIOS: wait for a key, al = ASCII
    cmp al, 13
    je .enter
    cmp al, 8
    je .backspace
    cmp al, 32
    jb .key
    cmp al, 126
    ja .key
    cmp cx, MAXLEN
    jae .key
    mov [di], al
    inc di
    inc cx
    call putc
    jmp .key
.backspace:
    jcxz .key
    dec di
    dec cx
    call putc                  ; al is still 8
    jmp .key
.enter:
    mov byte [di], 0
    call newline
    popa
    ret

; =====================================================================
;  Shell
; =====================================================================

; ZF = 1 if strings at si and di are equal
strcmp:
    push si
    push di
.loop:
    mov al, [si]
    cmp al, [di]
    jne .done
    test al, al
    jz .done
    inc si
    inc di
    jmp .loop
.done:
    pop di
    pop si
    ret

run_command:
    ; split "cmd args" at the first space
    mov si, input_buf
.find:
    mov al, [si]
    test al, al
    jz .setargs
    cmp al, ' '
    je .split
    inc si
    jmp .find
.split:
    mov byte [si], 0
    inc si
.skip:
    cmp byte [si], ' '
    jne .setargs
    inc si
    jmp .skip
.setargs:
    mov [args], si

    ; make the command lowercase so HELP and Help work too
    mov si, input_buf
.lower:
    mov al, [si]
    test al, al
    jz .lowered
    cmp al, 'A'
    jb .next_char
    cmp al, 'Z'
    ja .next_char
    add byte [si], 32
.next_char:
    inc si
    jmp .lower
.lowered:
    cmp byte [input_buf], 0
    je .ret

    mov bx, cmd_table
.next:
    mov di, [bx]
    test di, di
    jz .unknown
    mov si, input_buf
    call strcmp
    je .found
    add bx, 4
    jmp .next
.found:
    call [bx + 2]
    ret
.unknown:
    mov bl, ERROR_ATTR
    mov si, msg_unknown
    call puts_attr
    mov si, input_buf
    call puts
    mov si, msg_try_help
    call puts
.ret:
    ret

; =====================================================================
;  Commands
; =====================================================================

cmd_help:
    mov si, msg_help
    call puts
    ret

cmd_clear:
    call clear_screen
    ret

cmd_about:
    mov si, msg_about
    call puts
    ret

cmd_echo:
    mov si, [args]
    call puts
    call newline
    ret

cmd_time:
    mov ah, 0x02               ; BIOS: read real-time clock
    int 0x1A
    jc clock_error
    mov si, msg_time
    call puts
    mov al, ch
    call print_bcd
    mov al, ':'
    call putc
    mov al, cl
    call print_bcd
    mov al, ':'
    call putc
    mov al, dh
    call print_bcd
    call newline
    ret

cmd_date:
    mov ah, 0x04               ; BIOS: read date
    int 0x1A
    jc clock_error
    mov si, msg_date
    call puts
    mov al, ch                 ; century
    call print_bcd
    mov al, cl                 ; year
    call print_bcd
    mov al, '-'
    call putc
    mov al, dh                 ; month
    call print_bcd
    mov al, '-'
    call putc
    mov al, dl                 ; day
    call print_bcd
    call newline
    ret

clock_error:
    mov bl, ERROR_ATTR
    mov si, msg_noclock
    call puts_attr
    ret

cmd_mem:
    int 0x12                   ; BIOS: KB of base memory
    push ax
    mov si, msg_mem_base
    call puts
    pop ax
    call print_dec
    mov si, msg_kb
    call puts
    mov ah, 0x88               ; BIOS: KB of memory above 1 MB
    int 0x15
    jc .done
    push ax
    mov si, msg_mem_ext
    call puts
    pop ax
    call print_dec
    mov si, msg_kb
    call puts
.done:
    ret

cmd_color:
    movzx bx, byte [color_idx]
    inc bx
    cmp bx, NUM_COLORS
    jb .ok
    xor bx, bx
.ok:
    mov [color_idx], bl
    mov al, [colors + bx]
    mov [attr], al
    mov si, msg_color
    call puts
    ret

cmd_guess:
    xor ah, ah                 ; BIOS timer ticks = our random seed
    int 0x1A
    mov ax, dx
    xor dx, dx
    mov cx, 9
    div cx
    inc dl
    mov [secret], dl
    mov byte [tries], 0
    mov si, msg_guess_intro
    call puts
.ask:
    mov si, msg_guess_prompt
    call puts
.key:
    xor ah, ah
    int 0x16
    cmp al, 27                 ; Esc quits
    je .quit
    cmp al, '1'
    jb .key
    cmp al, '9'
    ja .key
    call putc
    call newline
    inc byte [tries]
    sub al, '0'
    cmp al, [secret]
    je .win
    jb .higher
    mov si, msg_lower
    call puts
    jmp .ask
.higher:
    mov si, msg_higher
    call puts
    jmp .ask
.win:
    mov bl, 0x0A
    mov si, msg_win
    call puts_attr
    movzx ax, byte [tries]
    call print_dec
    mov si, msg_win2
    call puts
    ret
.quit:
    call newline
    mov si, msg_quit
    call puts
    ret

cmd_reboot:
    mov si, msg_reboot
    call puts
.wait:
    in al, 0x64                ; wait for the keyboard controller...
    test al, 2
    jnz .wait
    mov al, 0xFE               ; ...then ask it to pulse the reset line
    out 0x64, al
    jmp 0xFFFF:0x0000          ; fallback: jump to the BIOS reset vector

cmd_shutdown:
    mov si, msg_shutdown
    call puts
    mov dx, 0x604              ; QEMU's ACPI power-off port
    mov ax, 0x2000
    out dx, ax
    mov dx, 0xB004             ; older QEMU / Bochs
    out dx, ax
    mov ax, 0x5301             ; APM, for real old PCs
    xor bx, bx
    int 0x15
    mov ax, 0x530E
    xor bx, bx
    mov cx, 0x0102
    int 0x15
    mov ax, 0x5307
    mov bx, 0x0001
    mov cx, 0x0003
    int 0x15
    mov bl, 0x0E               ; nothing worked: the classic message
    mov si, msg_safe
    call puts_attr
    cli
.halt:
    hlt
    jmp .halt

; =====================================================================
;  Data
; =====================================================================

cmd_table:
    dw s_help,     cmd_help
    dw s_clear,    cmd_clear
    dw s_about,    cmd_about
    dw s_echo,     cmd_echo
    dw s_time,     cmd_time
    dw s_date,     cmd_date
    dw s_mem,      cmd_mem
    dw s_color,    cmd_color
    dw s_guess,    cmd_guess
    dw s_reboot,   cmd_reboot
    dw s_shutdown, cmd_shutdown
    dw 0

s_help     db 'help', 0
s_clear    db 'clear', 0
s_about    db 'about', 0
s_echo     db 'echo', 0
s_time     db 'time', 0
s_date     db 'date', 0
s_mem      db 'mem', 0
s_color    db 'color', 0
s_guess    db 'guess', 0
s_reboot   db 'reboot', 0
s_shutdown db 'shutdown', 0

str_title    db 4, ' PebbleOS 0.1', 0
str_subtitle db 'a tiny operating system, built from scratch', 0
str_prompt   db 'pebble> ', 0

msg_welcome db "Welcome to PebbleOS! Everything you see is running on code we wrote,", 10
            db "with no Windows, Linux or anything else underneath.", 10
            db "Type 'help' to see what I can do.", 10, 10, 0

msg_help db "Commands:", 10
         db "  help      show this list", 10
         db "  clear     wipe the screen", 10
         db "  about     what is PebbleOS?", 10
         db "  echo X    say X back", 10
         db "  time      show the clock", 10
         db "  date      show today's date", 10
         db "  mem       how much memory this PC has", 10
         db "  color     change the text color", 10
         db "  guess     play a number guessing game", 10
         db "  reboot    restart the computer", 10
         db "  shutdown  turn the computer off", 10, 0

msg_about db "PebbleOS 0.1, a 16-bit operating system written in x86 assembly.", 10
          db "The boot sector is exactly 512 bytes. It loads the kernel from disk.", 10
          db "The kernel writes straight into video memory at 0xB8000 and asks", 10
          db "the BIOS for the keyboard, clock and memory size.", 10, 0

msg_unknown  db "Unknown command: ", 0
msg_try_help db "  (try 'help')", 10, 0
msg_time     db "The time is ", 0
msg_date     db "Today is ", 0
msg_noclock  db "The clock isn't answering.", 10, 0
msg_mem_base db "Base memory:     ", 0
msg_mem_ext  db "Extended memory: ", 0
msg_kb       db " KB", 10, 0
msg_color    db "New color!", 10, 0

msg_guess_intro  db "I'm thinking of a number from 1 to 9. (Esc to give up)", 10, 0
msg_guess_prompt db "Your guess: ", 0
msg_higher       db "Higher!", 10, 0
msg_lower        db "Lower!", 10, 0
msg_win          db "Correct! Guesses: ", 0
msg_win2         db 10, 0
msg_quit         db "Giving up already? :)", 10, 0

msg_reboot   db "Rebooting...", 10, 0
msg_shutdown db "Shutting down...", 10, 0
msg_safe     db "It is now safe to turn off your computer.", 0

colors     db 0x07, 0x0A, 0x0B, 0x0D, 0x0E, 0x0F, 0x0C
NUM_COLORS equ $ - colors

cur_x     db 0
cur_y     db 0
attr      db 0x07
color_idx db 0
secret    db 0
tries     db 0
args      dw 0
input_buf times MAXLEN + 1 db 0

; pad to exactly 8 KB (the boot sector loads 16 sectors).
; If the kernel ever grows too big, this line makes NASM complain.
times 8192 - ($ - $$) db 0

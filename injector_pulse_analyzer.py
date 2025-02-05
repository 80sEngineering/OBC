from rp2 import PIO, asm_pio    
    
    
@asm_pio(set_init=PIO.IN_LOW, autopush=True, push_thresh=32)
def period():
    wrap_target()
    set(x, 0)
    wait(0, pin, 0)  # Wait for pin to go low
    wait(1, pin, 0)  # Low to high transition
    label('low_high')
    jmp(x_dec, 'next') [1]  # unconditional
    label('next')
    jmp(pin, 'low_high')  # while pin is high
    label('low')  # pin is low
    jmp(x_dec, 'nxt')
    label('nxt')
    jmp(pin, 'done')  # pin has gone high: all done
    jmp('low')
    label('done')
    in_(x, 32)  # Auto push: SM stalls if FIFO full
    wrap()
    
    
    
@asm_pio(set_init=PIO.IN_LOW, autopush=True, push_thresh=32)
def pulse_width():
    wrap_target()
    set(x, 0)
    wait(0, pin, 0)  # Wait for pin to go low
    wait(1, pin, 0)  # Low to high transition
    label('low_high')
    jmp(x_dec, 'next') [1] # unconditional
    label('next')
    jmp(pin, 'low_high')  # while pin is high
    in_(x, 32)  # Auto push: SM stalls if FIFO full
    irq(0)
    wrap()

    
    


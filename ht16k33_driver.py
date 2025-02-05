from micropython import const
import framebuf
import logging
  
# Ordre : 0 DP N M L K J H G2 G1 F E D C B A

CHARS = (
    0b00000000, 0b00000000,  #
    0b01000000, 0b00000110,  # !
    0b00000010, 0b00100000,  # "
    0b00010010, 0b11001110,  # #
    0b00010010, 0b11101101,  # $
    0b00001100, 0b00100100,  # %
    0b00100011, 0b01011101,  # &
    0b00000100, 0b00000000,  # '
    0b00100100, 0b00000000,  # (
    0b00001001, 0b00000000,  # )
    0b00111111, 0b11000000,  # *
    0b00010010, 0b11000000,  # +
    0b00001000, 0b00000000,  # ,
    0b00000000, 0b11000000,  # -
    0b00000000, 0b00000000,  # .
    0b00100100, 0b00000000,  # /
    0b00001100, 0b00111111,  # 0
    0b00000000, 0b00000110,  # 1
    0b00000000, 0b11011011,  # 2
    0b00000000, 0b10001111,  # 3
    0b00000000, 0b11100110,  # 4
    0b00000000, 0b11101101,  # 5
    0b00000000, 0b11111101,  # 6
    0b00000000, 0b00000111,  # 7
    0b00000000, 0b11111111,  # 8
    0b00000000, 0b11101111,  # 9
    0b00010010, 0b00000000,  # :
    0b00001010, 0b00000000,  # ;
    0b00100100, 0b01000000,  # <
    0b00000000, 0b11001000,  # =
    0b00001001, 0b10000000,  # >
    0b01100000, 0b10100011,  # ?
    0b00000010, 0b10111011,  # @
    0b00000000, 0b11110111,  # A
    0b00010010, 0b10001111,  # B
    0b00000000, 0b00111001,  # C
    0b00010010, 0b00001111,  # D
    0b00000000, 0b11111001,  # E
    0b00000000, 0b01110001,  # F
    0b00000000, 0b10111101,  # G
    0b00000000, 0b11110110,  # H
    0b00010010, 0b00001001,  # I
    0b00000000, 0b00011110,  # J
    0b00001100, 0b01110000,  # K
    0b00000000, 0b00111000,  # L
    0b00000101, 0b00110110,  # M
    0b00001001, 0b00110110,  # N
    0b00000000, 0b00111111,  # O
    0b00000000, 0b11110011,  # P
    0b00100000, 0b00111111,  # Q
    0b00001000, 0b11110011,  # R
    0b00000000, 0b11101101,  # S
    0b00010010, 0b00000001,  # T
    0b00000000, 0b00111110,  # U
    0b00100100, 0b00110000,  # V
    0b00101000, 0b00110110,  # W
    0b00101101, 0b00000000,  # X
    0b00010101, 0b00000000,  # Y
    0b00100100, 0b00001001,  # Z
    0b00000000, 0b00111001,  # [
    0b00100001, 0b00000000,  # \
    0b00000000, 0b00001111,  # ]
    0b00001100, 0b00000011,  # ^
    0b00000000, 0b00001000,  # _
    0b00000001, 0b00000000,  # `
    0b00010000, 0b01011000,  # a
    0b00100000, 0b01111000,  # b
    0b00000000, 0b11011000,  # c
    0b00001000, 0b10001110,  # d
    0b00001000, 0b01011000,  # e
    0b00000000, 0b01110001,  # f
    0b00000100, 0b10001110,  # g
    0b00010000, 0b01110000,  # h
    0b00010000, 0b00000000,  # i
    0b00000000, 0b00001110,  # j
    0b00110110, 0b00000000,  # k
    0b00000000, 0b00110000,  # l
    0b00010000, 0b11010100,  # m
    0b00010000, 0b01010000,  # n
    0b00000000, 0b11011100,  # o
    0b00000001, 0b01110000,  # p
    0b00000100, 0b10000110,  # q
    0b00000000, 0b01010000,  # r
    0b00001000, 0b10001000,  # s
    0b00000000, 0b01111000,  # t
    0b00000000, 0b00011100,  # u
    0b00100000, 0b00000100,  # v
    0b00101000, 0b00010100,  # w
    0b00101000, 0b11000000,  # x
    0b00100000, 0b00001100,  # y
    0b00001000, 0b01001000,  # z
    0b00001001, 0b01001001,  # {
    0b00010010, 0b00000000,  # |
    0b00100100, 0b10001001,  # }
    0b00000101, 0b00100000,  # ~
    0b00111111, 0b11111111,

)

NUMBERS = (
    0x3F,  # 0
    0x06,  # 1
    0x5B,  # 2
    0x4F,  # 3
    0x66,  # 4
    0x6D,  # 5
    0x7D,  # 6
    0x07,  # 7
    0x7F,  # 8
    0x6F,  # 9
    0x77,  # a
    0x7C,  # b
    0x39,  # C
    0x5E,  # d
    0x79,  # E
    0x71,  # F
    0x40,  # -
)

_HT16K33_BLINK_CMD = const(0x80)
_HT16K33_BLINK_DISPLAYON = const(0x01)
_HT16K33_CMD_BRIGHTNESS = const(0xE0)
_HT16K33_OSCILATOR_ON = const(0x21)


class HT16K33:
    def __init__(self, i2c, address=0x70):
        self.i2c = i2c
        self.address = address
        self._temp = bytearray(1)
        self._blink_rate = 1
        self._brightness = 1
        self.buffer = bytearray(16)
        self._write_cmd(_HT16K33_OSCILATOR_ON)
        self.blink_rate(0)

    def _write_cmd(self, byte):
        self._temp[0] = byte
        self.i2c.writeto(self.address, self._temp)

    def blink_rate(self, rate=None):
        if rate is None:
            return self._blink_rate
        rate = rate & 0x03
        if rate != self._blink_rate:
            self._blink_rate = rate
            self._write_cmd(_HT16K33_BLINK_CMD |
                            _HT16K33_BLINK_DISPLAYON | rate << 1)
            
    def brightness(self, brightness=None):
        if brightness is None:
            return self._brightness
        brightness = max(0, min(brightness, 15))
        brightness = brightness & 0x0F
        if brightness != self._brightness:
            self._brightness = brightness
            self._write_cmd(_HT16K33_CMD_BRIGHTNESS | brightness)
        logging.info(f"> Brightness set to {brightness}")
        
    def show(self):
        self.i2c.writeto_mem(self.address, 0x00, self.buffer)

  
    def clear(self):
        for i in range(0, len(self.buffer)): self.buffer[i] = 0x00
        return self    
    
    
    def fill(self):
        fill = 0xff 
        for i in range(16):
            self.buffer[i] = fill


class Seg14x4(HT16K33):
    def scroll(self, count=1):
        if count >= 0:
            offset = 0
        else:
            offset = 2
        for i in range(6):
            print(i + offset)
            self.buffer[i + offset] = self.buffer[i + 2 * count]

    def put(self, char, index=0):
        if not 0 <= index <= 5:
            return
        if not 32 <= ord(char) <= 127:
            return
        if char == '.':
            self.buffer[index * 2 + 1] |= 0b01000000
            return
        c = ord(char) * 2 - 64
        self.buffer[index * 2] = CHARS[1 + c]
        self.buffer[index * 2 + 1] = CHARS[c]

    def put_text(self, text):
        k = len(text)
        for i in text:
            if i == '.' and len(text) - k > 0:
                self.put(char='.', index=len(text) - k - 1)
                continue
            self.put(char=i, index=len(text) - k)
            k -= 1
            
    def push(self, char):
        if char != '.' or self.buffer[7] & 0b01000000:
            self.scroll()
            self.put(' ', 3)
        self.put(char, 3)

    def text(self, text):
        for c in text:
            self.push(c)

     
    def zeros_before_number(self,number_str):
        if len(number_str) < 6:
            zeros_to_add = 6 - len(number_str)
            filled_number = '0' * zeros_to_add + number_str
        else:
            filled_number = number_str
        return filled_number

# -*- coding: utf-8 -*-
"""Модуль сборки командных пакетов для протокола динамометрического стенда."""

# System imports
from abc import ABC, abstractmethod

##########################################################


class BasePacketBuilder(ABC):
    """Базовый сборщик пакета вида HEADER + FORMAT + LEN + DATA + CRC."""

    _HEADER: bytes

    @classmethod
    def _build(cls, fmt: bytes, body: bytes) -> bytes:
        """Собирает пакет с указанным форматом и полезной нагрузкой."""
        if len(body) > 255:
            raise ValueError(f"Packet body is too long: {len(body)} bytes")

        packet_without_crc = cls._HEADER + fmt + bytes([len(body)]) + body
        return packet_without_crc + cls._compute_crc(packet_without_crc)

    @staticmethod
    def _compute_crc(data: bytes) -> bytes:
        """Считает контрольную сумму как сумму байтов по модулю 256."""
        return bytes([sum(data) & 0xFF])

# ------------------------------------------


class PacketBuilderDynamometer(BasePacketBuilder):
    """Базовый сборщик пакетов протокола текущего МК."""

    # Заголовок пакета, заданный в embedded-коде проекта.
    _HEADER = bytes([0xC8, 0x8C])

    @classmethod
    @abstractmethod
    def _packet_format(cls) -> bytes:
        """Возвращает байт формата пакета."""
        ...

# ------------------------------------------


class PacketBuilderDynamometerText(PacketBuilderDynamometer):
    """Сборщик текстовых команд для МК."""

    @classmethod
    def _packet_format(cls) -> bytes:
        """Возвращает формат командного пакета."""
        return bytes([0xAB])

    @classmethod
    def build_text_command(cls, text: str, encoding: str = "ascii") -> bytes:
        """Собирает командный пакет из текстовой команды."""
        return cls._build(cls._packet_format(), text.encode(encoding))

# ------------------------------------------


class PacketBuilderDynamometerBytes(PacketBuilderDynamometer):
    """Сборщик бинарных команд для МК."""

    @classmethod
    def _packet_format(cls) -> bytes:
        """Возвращает формат командного пакета."""
        return bytes([0xAB])

    @classmethod
    def build_byte_command(cls, body: bytes) -> bytes:
        """Собирает командный пакет из бинарной команды."""
        return cls._build(cls._packet_format(), body)

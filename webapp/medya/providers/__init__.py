"""Saglayici paketi — ICE AKTARIM KAYDI TETIKLER.

⚠ 11 Agu 2026 canli kuru testinde yakalandi: `avci.avla()` cagrildi ama
`kayit.aktif_saglayicilar()` BOS dondu ve butun sahneler "hicbir saglayici aday
dondurmedi" diye kapsam boslugu oldu. Sebep: `@kaydet` dekoratoru yalnizca
saglayici modulu IMPORT EDILDIGINDE kosuyor; agsiz testte modulleri elle
import ettigim icin hata maskelenmisti.

Bu dosya tum saglayicilari ice aktariyor; `avci` de bu paketi ice aktariyor.
Yeni saglayici eklerken buraya BIR SATIR eklemek yeterli.
"""
from . import acik_arsivler, stok  # noqa: F401

__all__ = ["acik_arsivler", "stok"]

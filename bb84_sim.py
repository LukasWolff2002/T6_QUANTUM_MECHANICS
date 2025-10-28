#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BB84 (Parte 1: sin intervención de Eve)
--------------------------------------
Este script implementa los pasos del esquema mostrado:
 1) Alice genera 1000 bits y 1000 bases aleatorias y los guarda en 'alice_bb84.txt'.
 2) Bob genera 1000 bases aleatorias y las guarda en 'bob_bb84_bases.txt'.
 3) Bob "mide": si la base coincide con la de Alice, conserva el bit; si no, lo deja vacío (None).
 4) Comparación de bases (canal clásico) para determinar coincidencias.
 5) Extracción de clave cruda (donde coinciden las bases).
 6) Verificación de errores: Bob revela una fracción de la clave y se estima la tasa de error.
 
Parámetros controlables:
- N_BITS: tamaño de la secuencia.
- SEED: semilla para reproducibilidad (None para aleatorio).
- NOISE_FLIP_PROB: prob. de volcar (flip) un bit correcto incluso con bases iguales (simula ruido).
- SAMPLE_FRACTION: fracción de la clave cruda que se revela para verificación (p.ej., 0.05 => 5%).
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

# ---------- Parámetros ----------
N_BITS = 1000
SEED = 42              # Cambia a None si quieres aleatoriedad no reproducible
NOISE_FLIP_PROB = 0.0  # 0.0 para canal perfecto (sin Eve, sin ruido)
SAMPLE_FRACTION = 0.05 # 5% de la clave cruda para test; también puedes fijar un número entero

# ---------- Utilidades ----------
BASES = ('R', 'D')

def rand_bits(n: int) -> List[int]:
    return [random.randint(0, 1) for _ in range(n)]

def rand_bases(n: int) -> List[str]:
    return [random.choice(BASES) for _ in range(n)]

def write_alice_file(path: str, bits: List[int], bases: List[str]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write("Bit\tBase\n")
        for b, B in zip(bits, bases):
            f.write(f"{b}\t{B}\n")

def write_bob_bases_file(path: str, bases: List[str]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write("Base\n")
        for B in bases:
            f.write(f"{B}\n")

def measure(bits: List[int], alice_bases: List[str], bob_bases: List[str], noise_flip_prob: float = 0.0) -> List[Optional[int]]:
    """Devuelve la lista de mediciones de Bob (None si las bases no coinciden)."""
    measured: List[Optional[int]] = []
    for bit, Ba, Bb in zip(bits, alice_bases, bob_bases):
        if Ba == Bb:
            m = bit
            # Simula ruido: con cierta probabilidad, se invierte
            if random.random() < noise_flip_prob:
                m ^= 1
            measured.append(m)
        else:
            measured.append(None)  # Entrada vacía si las bases no coinciden
    return measured

def extract_raw_key(alice_bits: List[int], measured: List[Optional[int]], alice_bases: List[str], bob_bases: List[str]) -> Tuple[List[int], List[int], List[int]]:
    """Devuelve (raw_key_alice, raw_key_bob, indices) donde indices son las posiciones mantenidas."""
    raw_A: List[int] = []
    raw_B: List[int] = []
    kept_idx: List[int] = []
    for i, (a, m, Ba, Bb) in enumerate(zip(alice_bits, measured, alice_bases, bob_bases)):
        if Ba == Bb and m is not None:
            raw_A.append(a)
            raw_B.append(m)
            kept_idx.append(i)
    return raw_A, raw_B, kept_idx

def sample_and_check(raw_A: List[int], raw_B: List[int], sample_fraction: float | int) -> Tuple[float, int, int]:
    """Muestra una fracción (o cantidad fija) y estima la tasa de error (QBER)."""
    n = len(raw_A)
    if n == 0:
        return 0.0, 0, 0
    k = sample_fraction if isinstance(sample_fraction, int) else max(1, int(round(n * sample_fraction)))
    k = min(k, n)
    idxs = random.sample(range(n), k)
    mismatches = sum(1 for i in idxs if raw_A[i] != raw_B[i])
    qber = mismatches / k
    return qber, mismatches, k

@dataclass
class Summary:
    n_bits: int
    n_matches: int
    n_discarded: int
    raw_key_length: int
    qber: float
    mismatches: int
    sample_size: int

    def __str__(self) -> str:
        lines = [
            f"Bits totales (N): {self.n_bits}",
            f"Coincidencias de bases: {self.n_matches}",
            f"Descartados (bases distintas): {self.n_discarded}",
            f"Largo de clave cruda: {self.raw_key_length}",
            f"QBER estimado (muestras): {self.qber:.4%}  ({self.mismatches}/{self.sample_size})"
        ]
        return "\n".join(lines)

def main():
    # Semilla
    if SEED is not None:
        random.seed(SEED)

    # Paso 1: Alice
    alice_bits  = rand_bits(N_BITS)
    alice_bases = rand_bases(N_BITS)
    write_alice_file("alice_bb84.txt", alice_bits, alice_bases)

    # Paso 2: Bob genera bases
    bob_bases = rand_bases(N_BITS)
    write_bob_bases_file("bob_bb84_bases.txt", bob_bases)

    # Paso 3: Bob mide
    measured = measure(alice_bits, alice_bases, bob_bases, noise_flip_prob=NOISE_FLIP_PROB)

    # Paso 4-5: Comparación de bases y extracción de clave cruda
    raw_A, raw_B, kept_idx = extract_raw_key(alice_bits, measured, alice_bases, bob_bases)

    # Paso 6: Verificación de errores
    qber, mismatches, sample_size = sample_and_check(raw_A, raw_B, SAMPLE_FRACTION)

    # Resumen
    n_matches = len(kept_idx)
    summary = Summary(
        n_bits=N_BITS,
        n_matches=n_matches,
        n_discarded=N_BITS - n_matches,
        raw_key_length=len(raw_A),
        qber=qber,
        mismatches=mismatches,
        sample_size=sample_size
    )

    # Guardar clave cruda (sin revelar las posiciones muestreadas)
    with open("raw_key_alice.txt", "w", encoding="utf-8") as fa, \
         open("raw_key_bob.txt", "w", encoding="utf-8") as fb:
        fa.write("".join(map(str, raw_A)) + "\n")
        fb.write("".join(map(str, raw_B)) + "\n")

    print("Archivos generados:")
    print(" - alice_bb84.txt")
    print(" - bob_bb84_bases.txt")
    print(" - raw_key_alice.txt")
    print(" - raw_key_bob.txt")
    print("\nResumen de la ejecución (sin Eve):")
    print(summary)

if __name__ == "__main__":
    main()

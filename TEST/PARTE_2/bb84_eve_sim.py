#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BB84 con intervención de Eve (Intercept-Resend)
-----------------------------------------------
Pasos implementados (como en tu esquema):
1) Eve genera 1000 bases aleatorias.
2) Eve mide con sus bases: si coinciden con las de Alice, obtiene el bit correcto; si no, el valor es aleatorio.
3) Eve reenvía a Bob los "qubits" re-codificados en SU base usando el bit que midió.
4) Bob mide con sus propias bases.
5) Se comparan bases Alice-Bob, se extrae la clave cruda y se estima el QBER revelando una fracción.

Archivos de salida principales:
- alice_bb84.txt                 (reutiliza formato Bit\tBase)
- eve_bb84_bases.txt             (bases de Eve)
- eve_measured_bits.txt          (bits medidos por Eve)
- bob_bb84_bases_eve.txt         (bases de Bob)
- raw_key_alice_eve.txt, raw_key_bob_eve.txt

Parámetros personalizables dentro del script.
"""
from __future__ import annotations
import random
from typing import List, Optional, Tuple
from dataclasses import dataclass

# ---------- Parámetros ----------
N_BITS = 1000
SEED = 123        # None para aleatorio no reproducible
SAMPLE_FRACTION = 0.05  # fracción de la clave revelada para verificación

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

def write_one_per_line(path: str, header: str, items: List[str]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header + "\n")
        for x in items:
            f.write(f"{x}\n")

def eve_intercept_resend(alice_bits: List[int], alice_bases: List[str], eve_bases: List[str]) -> Tuple[List[int], List[str]]:
    """
    Eve mide con sus bases. Si coincide con Alice, obtiene el bit correcto; si no, resultado aleatorio.
    Luego reenvía un nuevo "qubit" preparado en SU base (la de Eve) con el bit que midió.
    Para nuestra simulación clásica, esto equivale a devolver:
      - bits_enviados_a_bob (lo que Eve prepara tras medir)
      - bases_enviadas (que son exactamente las bases de Eve)
    """
    out_bits: List[int] = []
    for bit, Ba, Be in zip(alice_bits, alice_bases, eve_bases):
        if Ba == Be:
            measured = bit
        else:
            measured = random.randint(0, 1)  # valor aleatorio por proyección en base incorrecta
        out_bits.append(measured)
    # Eve envía en su propia base
    return out_bits, eve_bases[:]  # bits reenviados y bases de codificación

def bob_measure_against_eve(bits_from_eve: List[int], eve_bases: List[str], bob_bases: List[str]) -> List[Optional[int]]:
    """
    Bob mide los estados preparados por Eve. Si su base coincide con la base (de Eve) de preparación,
    obtiene el bit exacto; de lo contrario, el resultado es aleatorio (y en la práctica rompe la correlación).
    """
    measured: List[Optional[int]] = []
    for bE, Be, Bb in zip(bits_from_eve, eve_bases, bob_bases):
        if Be == Bb:
            measured.append(bE)
        else:
            measured.append(random.randint(0, 1))
    return measured

def extract_raw_key(alice_bits: List[int], bob_meas: List[Optional[int]], alice_bases: List[str], bob_bases: List[str]) -> Tuple[List[int], List[int], List[int]]:
    raw_A, raw_B, idx = [], [], []
    for i, (a, bm, Ba, Bb) in enumerate(zip(alice_bits, bob_meas, alice_bases, bob_bases)):
        if Ba == Bb and bm is not None:
            raw_A.append(a)
            raw_B.append(bm)
            idx.append(i)
    return raw_A, raw_B, idx

def sample_and_qber(raw_A: List[int], raw_B: List[int], sample_fraction: float | int) -> Tuple[float, int, int]:
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
    sifted_len: int
    discarded: int
    sample_size: int
    mismatches: int
    qber: float
    expected_qber_no_eve: float = 0.0
    expected_qber_with_eve: float = 0.25  # teórico ~25% en clave cribada

    def __str__(self) -> str:
        return (
            f"Bits totales: {self.n_bits}\n"
            f"Clave cruda (sifted): {self.sifted_len}\n"
            f"Descartados (bases distintas): {self.discarded}\n"
            f"Muestra revelada: {self.sample_size}\n"
            f"Errores en muestra: {self.mismatches}\n"
            f"QBER estimado: {self.qber:.2%}\n"
            f"QBER esperado (sin Eve): {self.expected_qber_no_eve:.0%}\n"
            f"QBER esperado (con Eve): {self.expected_qber_with_eve:.0%}"
        )

def main():
    # Semilla
    if SEED is not None:
        random.seed(SEED)

    # --- Alice ---
    alice_bits  = rand_bits(N_BITS)
    alice_bases = rand_bases(N_BITS)
    write_alice_file("PARTE_2/alice_bb84.txt", alice_bits, alice_bases)

    # --- Eve: pasos 1-3 ---
    eve_bases = rand_bases(N_BITS)
    bits_to_bob, bases_to_bob = eve_intercept_resend(alice_bits, alice_bases, eve_bases)
    write_one_per_line("PARTE_2/eve_bb84_bases.txt", "Base", list(bases_to_bob))
    write_one_per_line("PARTE_2/eve_measured_bits.txt", "Bit", [str(b) for b in bits_to_bob])

    # --- Bob: pasos 4-5 ---
    bob_bases = rand_bases(N_BITS)
    write_one_per_line("PARTE_2/bob_bb84_bases_eve.txt", "Base", list(bob_bases))
    bob_measured = bob_measure_against_eve(bits_to_bob, bases_to_bob, bob_bases)

    # Sifting (Alice vs Bob bases)
    raw_A, raw_B, kept = extract_raw_key(alice_bits, bob_measured, alice_bases, bob_bases)

    # Verificación (QBER)
    qber, mismatches, k = sample_and_qber(raw_A, raw_B, SAMPLE_FRACTION)

    # Guardar claves
    with open("PARTE_2/raw_key_alice_eve.txt", "w", encoding="utf-8") as fa, \
         open("PARTE_2/raw_key_bob_eve.txt", "w", encoding="utf-8") as fb:
        fa.write("".join(map(str, raw_A)) + "\n")
        fb.write("".join(map(str, raw_B)) + "\n")

    summary = Summary(
        n_bits=N_BITS,
        sifted_len=len(raw_A),
        discarded=N_BITS - len(kept),
        sample_size=k,
        mismatches=mismatches,
        qber=qber
    )

    print("Archivos generados:")
    print(" - alice_bb84.txt")
    print(" - eve_bb84_bases.txt")
    print(" - eve_measured_bits.txt")
    print(" - bob_bb84_bases_eve.txt")
    print(" - raw_key_alice_eve.txt")
    print(" - raw_key_bob_eve.txt")
    print("\nResumen (con Eve intercept-resend):")
    print(summary)

if __name__ == "__main__":
    main()

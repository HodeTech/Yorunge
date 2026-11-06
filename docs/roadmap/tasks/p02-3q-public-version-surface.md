---
id: P02-3q
phase: P02
status: draft
size: M
depends_on: [P02-3p, P02-3l]
capabilities: [C04, C13]
---
# P02-3q — Public `datasets versions` yüzeyi ve bağ artifact’ı

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 15. [ADR-0033](../../decisions/0033-dataset-version-references.md); ortak CLI/Python, P02-3l’nin ortak no-clobber yayın ilkesi.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı bir dataset’in sürümlerini görmek, bir sürüme değişmez referans üretmek ve sonra o referansın hâlâ geçerli olduğunu denetlemek ister.

## Giren ve girmeyen kapsam

`datasets versions list|show|bind|check` için ortak API/CLI; bağ artifact’ının P02-3l ortak yayın ilkesiyle no-clobber yayını (`--binding-out`); `--manifest` ile sayı eşliği; text/JSON/NDJSON, yardım, hata/exit eşlemesi; referans, CLI sözleşmesi, user-journeys, yetenek matrisi ve modül belgeleri girer. Sürüm oluşturma (P02-R4), eğitim planı bağı (P03-1) ve içerik üyeliği iddiası girmez.

## Bağımlılıklar ve kararlar

P02-3p ve P02-3l (ortak yayın ilkesi) verified olmalıdır. CLI/API için yorunge-contract-change disiplini uygulanır. [ADR-0033](../../decisions/0033-dataset-version-references.md) §1 sınırı: salt okuma.

## Sözleşme ve uygulama sınırı

[sürüm referansı sözleşmesi](../../reference/dataset-versions.md) içindeki yüzey. Yayın P02-3l’nin ortak ilkesini kullanır (kopya yok); `binding_*` hata kodları ayrıdır. Python karşılıkları senkron köprü kapılarını mevcut ailelerle aynı uygular. Genel `--output` yalnız biçimdir; hedef dosya `--binding-out`tur. Çıktı sır, ham gövde, `created_by`, `description` ve URL taşımaz.

## Kabul

1. `list` istenen sayfayı, `has_next` ve toplamı doğru gösterir; `show` detail+splits çapraz doğrulamasını; `bind` aynı sürüm ve aynı `--manifest` seçiminde aynı digest’i ve artifact’ı (0600, mevcut hedefi ezmeden) üretir; `check` unchanged=0, changed/missing=7, unavailable=mevcut kodlar.
2. Kısmi yayın sonrası belirsizlik `binding_write_uncertain`/5, kesin EEXIST `binding_output_exists`/2; parent/symlink yarışları ve hedef var senaryoları (P02-3l kapılarıyla).
3. JSON/NDJSON saf, TTY dışında prompt yok, BrokenPipe/SIGINT/Task.cancel mevcut 6/1/6 öncelikleriyle; sentinel testleri.
4. Kurulu CLI yolculuğu loopback üzerinde; belgeler çalışan komutlarla uyumlu.

## Doğrulama

CLI/API integration testleri, kurulu paket yolculuğu, belge/rehber kontrolleri, Ruff, strict mypy ve yorunge-contract-change denetim listesi.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.

---
id: P02-3q
phase: P02
status: draft
size: M
depends_on: [P02-3p]
capabilities: [C04, C13]
---
# P02-3q — Public `datasets versions` yüzeyi ve bağ artifact’ı

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 14. [ADR-0033](../../decisions/0033-dataset-version-references.md); ortak CLI/Python, no-clobber artifact.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı bir dataset’in sürümlerini görmek, bir sürüme değişmez referans üretmek ve sonra o referansın hâlâ geçerli olduğunu denetlemek ister.

## Giren ve girmeyen kapsam

`datasets versions list|show|bind|check` için ortak API/CLI; bağ artifact’ının root-dışı no-clobber yayını; `--manifest` ile sayı eşliği; text/JSON/NDJSON, yardım, hata/exit eşlemesi; referans, CLI sözleşmesi, user-journeys, yetenek matrisi ve modül belgeleri girer. Sürüm oluşturma (P02-R4), eğitim planı bağı (P03-1) ve içerik üyeliği iddiası girmez.

## Bağımlılıklar ve kararlar

P02-3p verified olmalıdır. CLI/API için yorunge-contract-change disiplini uygulanır. [ADR-0033](../../decisions/0033-dataset-version-references.md)#1 sınırı: salt okuma.

## Sözleşme ve uygulama sınırı

[sürüm referansı sözleşmesi](../../reference/dataset-versions.md) içindeki yüzey. Yayın, manifest yayıncısı kalıbını (veya P02-3l’deki ortak ilkeyi) kullanır; `binding_*` hata kodları ayrıdır. Python karşılıkları senkron köprü kapılarını mevcut ailelerle aynı uygular. Çıktı sır, ham gövde, `created_by`, `description` ve URL taşımaz.

## Kabul

1. `list` sayfayı ve `has_next`i doğru gösterir; `show` detail+splits çapraz doğrulamasını; `bind` aynı sürümde aynı digest’i ve artifact’ı (0600, mevcut hedefi ezmeden) üretir; `check` unchanged=0, changed/missing=7, unavailable=mevcut kodlar.
2. Kısmi yayın sonrası belirsizlik `binding_write_uncertain`/5, kesin EEXIST `binding_output_exists`/2; parent/symlink yarışları ve hedef var senaryoları.
3. JSON/NDJSON saf, TTY dışında prompt yok, BrokenPipe/SIGINT/Task.cancel mevcut 6/1/6 öncelikleriyle; sentinel testleri.
4. Kurulu CLI yolculuğu loopback üzerinde; belgeler çalışan komutlarla uyumlu.

## Doğrulama

CLI/API integration testleri, kurulu paket yolculuğu, belge/rehber kontrolleri, Ruff, strict mypy ve yorunge-contract-change denetim listesi.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.

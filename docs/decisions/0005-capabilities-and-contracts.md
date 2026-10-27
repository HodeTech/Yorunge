# ADR-0005: Kanıt ve kapsam bağlı yetenekler

**Durum:** Accepted. **Tarih:** 2026-10-27.

## Bağlam

API şeması, kılavuz, web istemcisi ve gerçek hesap erişimi farklı bilgiler verebilir. GPU rezervasyonu, genel runtime veya LLM fine-tuning yeteneğiyle eşdeğer değildir. Muadil araçlar da aynı model/parametre/çıktıları desteklemeyebilir.

## Karar

Yeteneğin görev, hizmet, hesap/proje, araç/sürüm ve ortam kapsamı saklanır. Runtime destek durumu `supported`, `unsupported`, `unknown`, `requires_access` olarak ifade edilir; kanıt türü, zaman ve son kullanma bilgisi eklenir. Uygulama teslim durumu ayrı matriste tutulur.

## Alternatifler

Tek `true/false` alanı bilinmeyen ve erişim eksikliği durumlarını karıştırır. Sabit bütün model/limit listesi bakım hatasına açıktır. Bir HTTP 403'ü global unsupported saymak yanlış ürün sonucu doğurur.

## Sonuçlar

Planlama daha açık ve hesap özelinde olur; bazı işlemler doğrulama bekler. Cache yenileme ve eski kanıt davranışı tasarlanmalıdır. [Yetenek kaydı](../reference/capability-record.md), [matris](../capability-matrix.md).

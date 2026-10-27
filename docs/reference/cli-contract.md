# CLI sözleşmesi

**Durum:** Tasarlanan v1 sözleşmesi; CLI henüz yok. **Tarih:** 2026-10-27.

## Komut alanları

| Aile | Planlanan işlemler | Aşama |
|---|---|---|
| `init`, `doctor`, `context`, `capabilities` | Başlangıç, profil/proje, tanılama, destek | P01 |
| `datasets` | inspect, upload, download, verify, versions | P02/P03 |
| `data` | LLM içeriği ingest, audit ve generate; görev bazlı tool seçimi | P03 |
| `catalog`, `models` | Arama, çözümleme ve sürüm/detail; araçlı fit, merge/export | P02 temel / P03 araç görevleri |
| `llm` | models, chat, embed, rerank, quota | P02 |
| `inference` | predict ve model/girdi uyumu | P02/P03 |
| `resources` | status, quota, reservations ve quote | P02/P03; yazma ayrıca kapılı |
| `train`, `evaluate` | plan ve run; task/tool/execution seçimi | P03 |
| `tools` | list ve açık check | P03 |
| `jobs` | list, show, watch, stop, reconcile | P01 temeli / P03 tam |
| `artifacts` | list, fetch, verify | P02/P03 |

İleri servis/MCP komutları P04 tasarımıyla eklenir. Yerel komutlar ağ veya sır okuma zorunluluğu taşımaz. Her ailede bütün fiillerin aynı fazda yayımlandığı varsayılmaz; kesin destek matrisi uygulama sürümünde daraltılabilir.

## Ortak seçenekler

`--profile`, `--project`, `--output text|json|ndjson`, `--non-interactive` ve gerektiğinde `--refresh`. Araçlı planlamada `--tool` ve `--execution` bulunur. `--tool` native veri/çıkarım işlemine gereksiz zorunluluk getirmez. TTY yalnız etkileşimi belirler; çıktı biçimini kendiliğinden JSON'a dönüştürmez.

**Örnekler taslaktır:**

```text
yorunge datasets inspect ./veri
yorunge llm models --profile work --output json
yorunge train plan --recipe training.yaml
yorunge train plan --recipe training.yaml --tool axolotl --execution local
yorunge train run --plan PLAN_ID --approve-plan PLAN_DIGEST
yorunge jobs watch OPERATION_ID --output ndjson
```

Onay seçeneği açık yürütme niyetini planla bağlar; kendi başına kriptografik insan kimliği kanıtı değildir. Güvenilen UI/CI/MCP host'unun yetkilendirme politikası ayrıca tanımlanır. Non-interactive çağrıda onay yoksa sessiz “evet” veya asılı prompt olmaz.

## Çıktı

- `text`: İnsan sonucu stdout; ilerleme/diagnostic stderr. Renk ve TUI kapatılabilir.
- `json`: Tek sonuç nesnesi stdout. Başlamadan/sonuçta başarısız komut stdout'u boş tutar, tek yapılandırılmış hata stderr'e yazar; kısmi operation kimliği hata içinde taşınır. İnsan ilerleme metni çıkmaz.
- `ndjson`: Destekleyen watch/stream komutunda her satır sürümlü olaydır. Başlatma öncesi hata stderr JSON'dur; başlamış akışın terminal başarısızlığı olayda yer alır. Akış sonunda başarılıymış gibi ek özet üretilmez.

Sonuç zarfı `schema_version`, `operation_id` (yoksa null), `status`, `data`, `warnings` taşır. Hata zarfında kararlı `code`, yerelleştirilebilir `message`, `operation_id`, `retryable` ve sınırlı `details` vardır. Tekil istek JSON çıktısı ile streaming NDJSON birbirine karışmaz. `--help`/`--version` insan odaklı meta işlemlerdir, operation oluşturmaz.

## Çıkış kodları

| Kod | Anlam |
|---:|---|
| 0 | İstenen iş/okuma tamamlandı |
| 1 | Kesin operasyon/uzak servis başarısızlığı |
| 2 | Kullanım, config/şema veya yerel önkoşul hatası |
| 3 | Kimlik/erişim eksik veya reddedilmiş |
| 4 | Gerekli onay sağlanmadı |
| 5 | Yan etkili işlemin sonucu belirsiz; uzlaştırma gerekli |
| 6 | İşlem iptal edildi |
| 7 | İçerik/artefakt bütünlüğü uyuşmazlığı |

Salt okunur capability sorgusu başarıyla bilinmiyor sonucu döndürürse kod 0 olabilir; belirsiz **yan etki** kod 5'tir. Haricî aracın ham kodu `provider_exit_code` olarak ayrıca saklanır. Örneğin ForgeLM'in kod 6'sı Yörünge'de otomatik iptal sayılmaz; adaptör anlamını eşler.

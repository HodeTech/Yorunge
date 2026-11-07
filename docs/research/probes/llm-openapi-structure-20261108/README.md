# LLM OpenAPI yapısal özeti

**Durum:** Araştırma aracı; ürün kodu veya kabul kanıtı değildir. Sağlayıcı şemasının her yeniden okumasında "ne değişti" sorusunu, şema gövdesini depoya koymadan cevaplamak için vardır.

[structure.json](structure.json), 2026-11-08'de credentialsız tek GET ile okunan [LLM OpenAPI](https://evren-llmapi.ssyz.org.tr/openapi.json) gövdesinin (53.649 byte, SHA-256 `e2254a302d6108dcd715151f8f2310195b86439ac7f1686959df908a0f2a700e`) [summarize.py](summarize.py) çıktısıdır. Özet kaynak kimliğini, her operasyonu (yöntem, yol, parametre, gövde ve yanıt kodu), her bileşen şemasının alan adlarını, nullability dahil sıkıştırılmış tiplerini ve zorunlu alanlarını taşır. Açıklama metinleri saklanmaz; her açıklamanın kısa SHA-256 özeti tutulur, böylece anlam değişimi metin olmadan görünür.

## Yeniden okuma

```sh
curl -sS https://evren-llmapi.ssyz.org.tr/openapi.json -o .local/openapi-new.json
.venv/bin/python -I docs/research/probes/llm-openapi-structure-20261108/summarize.py .local/openapi-new.json > .local/structure-new.json
diff docs/research/probes/llm-openapi-structure-20261108/structure.json .local/structure-new.json
```

`source` farkı gövdenin değiştiğini, `operations`/`schemas` farkı yapısal değişimi, yalnız `#özet` veya `text` farkı yalnız açıklama değişimini gösterir. Yeni özet ilgili kanıt kaydına eklenir; `structure.json` değiştirilmez, tarihli yeni bir dizin açılır. Betik yalnız yerel dosya okur, ağ kullanmaz, çift anahtarlı veya OpenAPI olmayan girdiyi reddeder.

## Ağsız kontrol

```sh
.venv/bin/python -m pytest docs/research/probes/llm-openapi-structure-20261108/test_summarize.py -q
```

Yedi vaka yalnız sentetik belge kullanır: sıralama bağımsızlığı, nullability ve açıklama değişiminin görünmesi, çift anahtar/bozuk girdi reddi. Bu özet şemanın doğruluğunu veya hesap davranışını kanıtlamaz; yalnız o gün okunan gövdenin yapısını sabitler.

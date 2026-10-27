# LLM ve çıkarım modülü

**Durum:** Planlandı. **Kapsam:** C06/C07/C15. **Faz:** P02–P04.

Metin/akış, embedding, rerank ve görsel çıkarım görevlerini hizmete uygun girdi/çıktı biçimiyle yürütür. OCR/ses gibi ileri servisler, model ve sözleşme desteği doğrulanınca aynı alana eklenir. Bu işlemler eğitim aracı kurulmasını gerektirmez.

**Girdi:** Görev, model, context ve doğrulanmış içerik. **Çıktı:** Göreve özel sonuç, provider request kimliği ve bilinen kullanım bilgisi. Haricî araç için öğretmen/judge modeli seçimi bu servis yetenekleriyle ilişkilendirilir; aracın kendi ağ davranışı ayrıca doğrulanır.

Akış; sıralama, bitiş nedeni, gömülü hata ve yarım yanıt için açık semantik taşır. Eksik üretim tam cevap olarak dönmez. Girdi/çıktı ve toplam süre sınırı uygulanır; retry sadece güvenli aşamada ve tek bütçeden yapılır. Aynı hesabın anahtarları bağımsız kota havuzu sayılmaz.

**Kabul:** Normal JSON/SSE, bozuk/boş model cevabı, karar/OCR modelinin yanlış göreve seçilmesi, 429/403, kesilen akış, client cancellation ve stdout saflığı sınanır. SDK'nın desteği kendi testimiz yerine geçmez.

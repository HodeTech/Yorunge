# P00 — Ürün ve dokümantasyon temeli

**Durum:** Tamamlandı — belge temeli. **Tarih:** 2026-10-27. **Kapsam:** Bu çalışma.

## Amaç

Uygulamaya başlamadan neyin geliştirileceğini, araç/ortam seçimini, kullanım ve performans beklentisini anlaşılır bir temele bağlamak.

| İş | Teslim |
|---|---|
| P00-1 | Boş GitHub reposunu istenen yerel dizine klonlamak |
| P00-2 | Platform kapsamı, kullanıcı yolculukları ve yetenek durumunu tanımlamak |
| P00-3 | ForgeLM varsayılanı ve seçilebilir muadil sözleşmesini kurmak |
| P00-4 | Mimari, modül sınırları, standartlar ve ADR'leri oluşturmak |
| P00-5 | MIT ve root katkı/güvenlik/ajan belgeleri, faz ve araştırma haritasını oluşturmak |
| P00-6 | Dosya/bağlantı, durum, komut örneği ve kapsam tutarlılığını doğrulamak |

## Çıkış ölçütü

Her doküman kendi kanonik indeksinden bulunabilir; yerel linkler ve kod blokları tutarlıdır. Dokümanlar kişisel mutlak yola veya başka checkout'a bağlı değildir. Planlanan komutlar açıkça taslaktır. Native EVREN görevleri ForgeLM'e zorlanmaz; uygun görevlerde default ve muadil kabul koşulu nettir. Runtime erişimi ve uygulanmış özellik iddiaları kanıtı aşmaz.

Bu fazın tamamlanması ürünün çalıştığı veya yayınlandığı anlamına gelmez. Uygulama testleri P01'de gerçek paket kurulunca başlar. Son kontrol kaydı bu dosyaya özet olarak eklenir; kullanıcı/hesap verisi tutulmaz.

## Teslim kontrolü — 27 Ekim 2026

67 Markdown belge ve toplam 71 dosya oluşturuldu. 151 yerel bağlantı çözüldü; bütün Markdown belgeler root README'den erişilebilir. Tek H1, kapalı kod blokları, alt dizin indeksleri, sıralı 7 ADR ve kişisel mutlak yol bulunmaması denetlendi. Kaynak koda verilen iki sabit commit/satır bağlantısı da kontrol edildi.

Profil TOML'i ve reçete YAML'ı gerçek parser'larla okundu; profilin görev bazlı ForgeLM varsayılanı ve reçetenin görev/ortam alanları tutarlı. Bu yalnız sözdizimi ve doküman içi tutarlılık denetimidir; runtime config doğrulaması değildir. Üç Mermaid bloğu okunarak kontrol edildi; otomatik render yapılmadı. Uygulama veya canlı EVREN testi yapılmış gibi sonuç kaydı üretilmedi.

## Gözden geçirme sonrası kontrol — 27 Ekim 2026

Paylaşılabilir kapsam yeniden sayıldı: 68 Markdown, toplam 72 dosya ve 161 yerel bağlantı. Bütün Markdown belgeler root README'den erişilebilir; bağlantı hedefleri ve üç anchor, tek H1, kapalı fence'ler, alt dizin indeksleri, sıralı 7 ADR, UTF-8/LF ve kişisel mutlak yol bulunmaması denetlendi. Seçilmiş sır örüntülerinde eşleşme görülmedi; bu kapsamlı bir sır taraması sertifikası değildir. Önceki teslim kaydı tarihsel ölçüm olarak korundu.

Bir TOML ve bir YAML örneği gerçek parser'larla yeniden okundu. Planın hizmet/yetki/digest bağları, capability cache kapsamı, doğrulanmış iptal geçişleri ve P01 iş sırası belge düzeyinde eşitlendi. Git dışı yerel dosyaların dışlaması kontrol edildi; paket/site çıktısı henüz bulunmadığı için çıktı dışlama kontrolü çalıştırılmadı.

Üç Mermaid bloğu render edilmedi. Uygulama/paket/CI olmadığı için runtime testi çalıştırılmadı; canlı hesap işlemi yapılmadı. Özel güvenlik bildiriminin kullanılabilirliği ve yedek kanal, `SECURITY.md` ile B12'de ilk yayın öncesi açık koşul olarak kayıtlıdır.

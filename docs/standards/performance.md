# Performans ve optimizasyon standardı

**Durum:** Benimsenmiş hedefler; henüz benchmark yapılmadı. **Tarih:** 2026-10-27.

Performans; kullanıcı bekleme süresi, tepe bellek, ağ/disk işi ve API/kota tüketimiyle ölçülür. Daha az satır kod veya daha çok paralel iş tek başına iyileşme sayılmaz.

## Başlangıç bütçeleri

| Yol | İlk kabul hedefi | Ölçüm sınırı |
|---|---|---|
| `--help`, `--version` | Referans ortamda sıcak p95 ≤ 500 ms | En az 30 ayrı süreç; ağ/DB/sır/GPU import yok |
| Yerel profil/önbellek okuma | Sıcak p95 ≤ 200 ms | Veri boyutu ve disk türü kayıtlı; uzak istek hariç |
| Büyük dosya aktarımı | 1 GiB dosyada istemci ek RSS ≤ 64 MiB | Eğitim süreçleri ayrı ölçülür; worker/chunk/buffer sınırı kayıtlı |
| Aktarım belleği | Dosya boyutuyla doğrusal büyümeme | 16 MiB, 256 MiB, 1 GiB fixture karşılaştırması |
| Kuyruk ve eşzamanlılık | Sınırlı worker + byte bütçesi | Başlangıç varsayılanı aktarımda 2 worker; hizmet limitinden düşük tutulur |
| Ağ işlemi | Açık connect/read/total deadline ve deneme bütçesi | Uç ve iş türü bazında; toplam bekleme sınırsız olamaz |

Bu değerler hedef olarak seçildi; donanım/Python/işletim sistemi, veri ve komut kaydedilmeden sonuç kıyaslanmaz. İlk gerçek ölçüm sonrası gerekçeli değişiklik yapılabilir; başarısız hedef sessizce gevşetilmez. Soğuk açılış ve kurulum boyutu ayrıca raporlanır.

## Veri, ağ ve hesap verimliliği

Dosyalar bloklu hash/stream ile işlenir. Aynı disk üzerinde gereksiz paralel hash taraması yapılmaz. Hash önbelleği güncel içerik kanıtı yerine geçmez; değişmez snapshot veya güvenilir yeniden doğrulama stratejisi gerekir. Yükleme kuyruğu sadece dosya sayısını değil buffer baytını da sınırlar.

Listelemede N+1 çağrısı ölçülür; varsa sunucunun batch/sayfalama/koşullu GET yetenekleri kullanılır. Desteklenmeyen batch endpoint uydurulmaz. Model/yetenek önbelleği hesap/hizmet/sürüm ve son doğrulama zamanı taşır. Maliyet ve yetki kararı eski önbellekle kesinleştirilmez.

İzleme aralığı iş durumu ve sağlayıcı limitine göre uyarlanır; etkin olmayan iş yüksek frekansta sorgulanmaz. Backoff, jitter, `Retry-After` ve tüm işlem deadline'ı birlikte uygulanır. SDK/uygulama katmanlarında çarpan retry oluşmaz. Bağlantı havuzu kullanılır; tek komut gereksiz arka plan daemon'u başlatmaz.

## Darboğaz doğrulaması

Ölçüm; hazırlık/hash, bekleme, aktarım, uzak çalışma ve çıktı toplama sürelerini ayırır. Bir optimizasyon PR'ı başlangıç/son ölçümü, veri doğruluğunu ve kaynak etkisini içerir. Aşırı yükte kontrollü ret/backpressure beklenir. GPU modeli/hizmeti yavaş olduğunda gecikme Yörünge CPU optimizasyonu diye raporlanmaz.

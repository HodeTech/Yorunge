# Mevcut durum ve sıradaki iş

**Güncellendi:** 2026-10-27.

## Bugün

- Repo boş olarak klonlandı; önceki kullanıcı dosyası veya uygulama yoktu.
- Yörünge'nin EVREN kapsamlı yardımcı araç konumu ve ForgeLM varsayılan/seçilebilir araç modeli belgelendi.
- Root belgeleri, MIT, ürün kapsamı, standartlar, mimari, modüller, ADR'ler, sözleşmeler ve faz planları hazırlandı.
- P00 belge bütünlüğü/tutarlılık kontrolü tamamlandı: yerel bağlantılar, başlıklar, kod blokları, indeks erişimi ve config örneklerinin sözdizimi doğrulandı. Henüz uygulama, paket, CI workflow'u veya runtime testi yok.
- Yerel analiz arşivi `docs/analysis/private/` altında Git ve yayın kapsamından dışlandı. Paylaşılabilir belgeler bu arşive veya içindeki proje/deney kayıtlarına referans vermez.

## Sıradaki uygulama dilimi

P01-1 ile gerçek Python paket/CLI/HTTP/şema seçimini küçük deneyle kur; `--help`, cold/warm başlangıç, opsiyonel import ve makine stdout davranışını ölç. P01-2'de config/context/secret referansları, P01-3'te capability ve offline plan modeli gelir. P01-4'te kalıcı operation/lease, P01-5'te ortak hizmet/sonuç portları ve CLI/Python hattı eklenince tek offline görev sahte execution ve artefakt sonucuna kadar uçtan uca yürütülür. Kabul sınırları [P01 iş tablosundadır](phase-01-core.md).

Paralel ürün araştırması P02 veri/çıkarım kullanıcı görevlerini ve EVREN'in güncel kimlik/şema sınırını doğrular. P03 için ForgeLM ile bir muadil aynı görevde seçilir; gerçek adaptör uygulanmadan destek etiketi verilmez.

## Şu an çözülmemiş dış sorular

EVREN workspace genel kullanıcı erişimi, haricî paket/araç kurulum yöntemi, kalıcı artefakt, managed LLM eğitim API'si ve kullanıcı LLM serving sözleşmesi. Bunlar bütün ürünü durdurmaz; ilgili özelliğin durumunu sınırlar. [Araştırma soruları](../research/validation-questions.md), [backlog](backlog.md).

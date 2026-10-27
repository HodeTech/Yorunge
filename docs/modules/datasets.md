# Veri setleri modülü

**Durum:** Planlandı. **Kapsam:** C03/C04. **Faz:** P02/P03.

Yerel dosya denetimi, manifest, private veri seti oluşturma, dosya/ZIP aktarımı, indirme, resume/reconcile ve sürüm/bölme bilgisi bu modüldedir. Etiketleme editörü kurmaz; mevcut veri/etiket yapısını kontrol eder ve uygun import yolunu seçer.

Presign → PUT → confirm ile etiketli ZIP import ayrı sözleşmelerdir. Dosyanın güncel hash'i ve kök sınırı gönderim öncesi doğrulanır. Büyük içerik stream edilir; worker/byte kuyruğu sınırlıdır. Sunucu hash dedup yapıyorsa farklı yerel dosya kimliklerinin tek uzak öğeye bağlanması raporlanır; isim ve kayıt sayısı sessizce kaybolmaz.

Manifest/günlük tek gerçek kaynak değildir. Uzak öğe silinmiş, yerel dosya değişmiş veya confirm bozulmuşsa resume bunu açıklar. Verify sonucu yerel hash, uzak metadata ve isteğe bağlı uzak byte doğrulamasını ayrı bildirir. Sürüm oluşturma/freeze gibi ek yan etkiler planın içinde görünür olmalıdır.

**Kabul:** Aynı boyutta değişim, symlink, bozuk manifest, çift dosya/hash, kesik PUT, yanlış confirm, stale journal, sayfalama ve indirme no-clobber senaryoları geçer. Kullanıcı veri seti kimliği ve eksik/kalan iş raporu alır. [Aktarım yolu](../user-journeys.md).

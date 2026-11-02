# Veri setleri modülü

**Durum:** Uygulanıyor; yerel alt küme çalışma dalında verified, PR #13 kullanıcı incelemesinde. **Kapsam:** C03/C04. **Faz:** P02/P03.

Yerel alt küme [P02-1 planıyla](../roadmap/p02-1-delivery-plan.md) çalışma dalında tamamlandı. [ADR-0023](../decisions/0023-local-dataset-manifests.md) ve [Manifest v1](../reference/dataset-manifest.md) Accepted; inspect/verify CLI/Python ve no-clobber yayın çalışma dalında uygulandı; kod review’ları, üç temiz kurulum turu ve kaynak bağlı native kabulü tamamlandı. Üç ortam source/metadata CI ve kalıcı kanıt kabulü geçti; [PR #13](https://github.com/HodeTech/Yorunge/pull/13) kullanıcı incelemesindedir. İlk dilim normal dosya ad/byte envanteridir; aşağıdaki upload/ZIP/sürüm ve içerik-formatı hedefleri uygulanmış değildir.

## Planlanan uzak veri iş akışları

Yerel dosya denetimi, manifest, private veri seti oluşturma, dosya/ZIP aktarımı, indirme, resume/reconcile ve sürüm/bölme bilgisi bu modüldedir. Etiketleme editörü kurmaz; mevcut veri/etiket yapısını kontrol eder ve uygun import yolunu seçer.

Presign → PUT → confirm ile etiketli ZIP import ayrı sözleşmelerdir. Dosyanın güncel hash'i ve kök sınırı gönderim öncesi doğrulanır. Büyük içerik stream edilir; worker/byte kuyruğu sınırlıdır. Sunucu hash dedup yapıyorsa farklı yerel dosya kimliklerinin tek uzak öğeye bağlanması raporlanır; isim ve kayıt sayısı sessizce kaybolmaz.

Manifest/günlük tek gerçek kaynak değildir. Uzak öğe silinmiş, yerel dosya değişmiş veya confirm bozulmuşsa resume bunu açıklar. P02-2/3’te planlanan aktarım doğrulaması yerel hash, uzak metadata ve isteğe bağlı uzak byte doğrulamasını ayrı bildirecek; bugünkü datasets verify yalnız yerel Manifest v1 ile yeniden hash’lenen dosya kümesini karşılaştırır. Sürüm oluşturma/freeze gibi ek yan etkiler planın içinde görünür olmalıdır.

**Kabul:** Aynı boyutta değişim, symlink, bozuk manifest, çift dosya/hash, kesik PUT, yanlış confirm, stale journal, sayfalama ve indirme no-clobber senaryoları geçer. Kullanıcı veri seti kimliği ve eksik/kalan iş raporu alır. [Aktarım yolu](../user-journeys.md).

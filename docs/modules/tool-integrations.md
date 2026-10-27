# Haricî araç entegrasyonları modülü

**Durum:** Planlandı. **Kapsam:** C09/C10. **Faz:** P03.

ForgeLM ve muadillerin manifest, sürüm kontrolü, parametre/veri dönüşümü, execution hazırlığı ve sonuç normalizasyonunu sahiplenir. Tercih çözümleme iş akışı politikasındadır; adaptör kendisini global default yapmaz.

Varsayılan ForgeLM, uygun görevde kullanıcıya hazır seçim sunar. Uyumlu kurulum yoksa açık hata/ortam bilgisi döner. Alternatifler aynı task/result sözleşmesini uygular; araç özel seçenekler kaybolmaz. İlk release'te en az bir muadil aynı görevle doğrulanmalıdır.

Süreç argv olarak başlatılır, shell interpolation ve örtük plugin import yoktur. Gerekli secret/env kapsamı tanımlanır; kullanıcının bütün credential ortamı düşünmeden alt sürece aktarılmaz. Araçların kendi HTTP, telemetry, cache ve dosya davranışı entegrasyon incelemesinin parçasıdır.

**Kabul:** Versiyon uyumsuzluğu, bulunamayan binary, kayıplı config, yanlış output role, iptal/timeout ve integrity senaryoları ortak testten geçer. Unsloth'un başka aracın backend'i olması bağımsız sağlayıcı olarak doğrulandığı anlamına gelmez. [Araç portu](../reference/tool-provider-contract.md).

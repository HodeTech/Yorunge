# P04 — Otomasyon, ileri görevler ve yayın kapısı

**Durum:** Planlandı; bazı alanlar dış erişime bağlı. **Bağımlılık:** Önceki temel kullanım senaryolarının kabulü.

| İş | Çıktı | Ek kapı |
|---|---|---|
| P04-1 | Aynı çekirdeğe bağlı MCP | Host onayı, kaynak/deadline ve araç çıktısı güven sınırı |
| P04-2 | Doğrulanmış ileri LLM/medya görevleri | Model/görev ve büyük girdi/çıktı sözleşmesi |
| P04-3 | EVREN workspace execution | Genel/pilot kullanıcı erişimi, kurulum/GPU/ağ/disk/süre/artefakt kanıtı |
| P04-4 | Gerekirse gelişmiş terminal/yerel köprü | Gerçek kullanıcı ihtiyacı, local auth/framing/bellek ve araç uyumu |
| P04-5 | Rezervasyon/yayınlama/silme kapsamını genişletme | İşleme özgü etki/önizleme/yetki/uzlaştırma |
| P04-6 | İlk dağıtım ve işletim kabulü | Paket içeriği, destek matrisi, CI, migration/recovery, UX ve performans kanıtı |

## Runtime kabulü

İzinli küçük bir ForgeLM veya seçilmiş muadil işi gerçekten GPU'da eğitilir; adapter/model, checkpoint ve kanıt dosyaları ortam dışına alınır. Süre sonu/iptal/restart davranışı ve maliyet kaydı doğrulanır. Sadece notebook açılması, CUDA'nın görünmesi veya kamu envanteri yeterli değildir.

## Yayın kabulü

Kurulumdan ilk başarıya kadar uçtan uca kullanıcı denemesi; bozuk veri/ağ/disk durumları; gerçek bağımlılık/paket/sır dışlama; çalışma zamanı ve belge sürüm tutarlılığı gerekir. Özellik matrisi yalnız desteklenen sürüm ve kanıtlı görevleri yayımlandı yapar. Erişimi kapalı özellikler ilk ürün yayınının gizli zorunluluğu değildir; açık biçimde kapalı kalabilir.

Kaynak tüketimi ve kullanıcı kolaylığı önceki fazlarda geçilmiş olmalıdır; bu fazın “hardening” adı temel kontrollerin ertelenmesine gerekçe olmaz. Kullanıcı modeli serving ayrı doğrulama olmadan dosya export başarısından türetilmez.

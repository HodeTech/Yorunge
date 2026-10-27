# Roadmap, belge ve ajan hazırlığı review'si

**Tarih:** 2026-10-27. **Taban:** `4bfce4e` development. **Kapsam:** Aktif ürün implementasyonundan önce yol haritası ve ajan çalışma düzeni. Canlı EVREN, eğitim veya release deneyi değildir.

## Sonuç

Ürün yönü, hafif çekirdek, dört bağımsız eksen, sır/yan etki sınırı ve kanıt durumu doğru kurulmuştu. Faz belgeleri epik seviyesinde yararlıydı; doğrudan bir ajana verilecek işin büyüklüğü ve özellikle kimlik/state sırası yeterince belirli değildi. Yakın iş şimdi tek `ready` kartla, sonraki epikler ise açık bölünme ve dış kapılarla gösteriliyor. Bu, bütün gelecek fazların implementasyona hazır olduğu anlamına gelmez.

## Bulgular ve yapılan düzeltmeler

Önem, dokümanın geliştirmeyi yanlış yönlendirme etkisini belirtir; doğrulanmış runtime güvenlik açığı sınıflaması değildir. Satır referansları inceleme tabanına aittir.

| Bulgu | Taban kanıtı | Etki ve düzeltme |
|---|---|---|
| R1 — Önemli: kimlik/state bağımlılığı açık değil | [P01:10–12](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/roadmap/phase-01-core.md#L10) | Kimlik nesli için kalıcılık gereği iş sırasına yansımıyordu. Env çözümleme P01-2a; store P01-4a; nesil P01-2b; capability/plan ve operation daha sonra. B13 kararı açık kayıt oldu. |
| R2 — Önemli: çok sonuçlu satırlar tek iş gibi okunabiliyor | [P02:11](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/roadmap/phase-02-data-and-inference.md#L11), [P03:11](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/roadmap/phase-03-training-and-tools.md#L11) | Chat/stream/embed/rerank/vision ve veri/eval/merge/export tek implementasyon sanılabilirdi. İlk dar sonuç, bağımlı hat ve bölünmesi gereken L kapsamı ayrı yazıldı. |
| R3 — Önemli: yayınla opsiyonel gelişmiş kapsam arasındaki sınır yoruma açık | [P04:12](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/roadmap/phase-04-automation-and-hardening.md#L12) | MCP/runtime/media bitmeden hiçbir şey yayımlanamaz veya temel recovery sonra yapılır gibi iki farklı okuma mümkündü. Koşullu hatlar ile zorunlu release kanıtı ayrıldı; ürünün ilk kullanılabilir hedefleri ve kullanıcı kapsam kararı korundu. |
| R4 — Orta: yakın işin tek kabul kaynağı/hazırlık durumu yok | [current](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/roadmap/current.md) | `ready`/`partial`/`verified` iş semantiği ve S/M/L boyut sınırı eklendi. Yalnız P01-2a için gerçek kart açıldı; current karta yönlendiriyor, kabulü çoğaltmıyor. |
| R5 — Orta: bazı capability/CLI hedeflerinin faz karşılığı örtük | [P02](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/roadmap/phase-02-data-and-inference.md), [P04](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/roadmap/phase-04-automation-and-hardening.md) | Yerel init/doctor ve jobs okuma P01-2c/P01-4c'ye, hesap/org/proje keşfi P02-0b'ye, sürüm/bölme bağları P02-3'e ve serving araştırması P04-R1/B07'ye bağlandı. Export serving sayılmadı; C17 implementasyonu hâlâ dış kapı ve ayrı kapsam kararı gerektiriyor. |
| R6 — Orta: yolculuk durum etiketi koddan geride | [journeys:3](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/user-journeys.md#L3), [journeys:33](https://github.com/HodeTech/Yorunge/blob/4bfce4e/docs/user-journeys.md#L33) | Artık çalışan context/plan komutları da tümüyle taslak görünüyordu. Bugünkü offline alt küme ve henüz uygulanmayan uçtan uca deneyim ayrıldı; gerçek sentetik örnek kullanıldı. |
| R7 — Orta: ajan kuralları var, tekrar eden prosedür/routing yok | [AGENTS](https://github.com/HodeTech/Yorunge/blob/4bfce4e/AGENTS.md) | Altı dar skill, ilgili bağlam eşlemesi ve ortak katalog eklendi. Yetki genişleten hook/model/global ayar veya bütün katalog yükleme gereği eklenmedi. |
| R8 — Orta: belge kontrolü yeni kart/skill alanlarını kapsamıyor | [checker:23](https://github.com/HodeTech/Yorunge/blob/4bfce4e/scripts/check-docs.py#L23) | Açık kaynak listesi yeni materyale genişletildi; frontmatter ve kod örneği başlıkları ayrıldı. Metadata, alias ve ready bağımlılığı için gerçek negatif testli helper CI'ya bağlandı. |

R1–R8 bu değişiklikte ele alındı. P00 tarihsel kabul kayıtları, ürün kapsamı ve dış hizmet kanıtları yeniden yazılmadı. B02/B13 gibi henüz alınmamış teknik kararlar alınmış veya kodlanmış gösterilmedi.

## Diğer belge kümeleri

Ürün/kabiliyet matrisi amaç ve teslim durumunu, modüller alan sahipliğini, mimari bağımlılık/güven sınırını, referanslar uygulanmış dar şema ile gelecekteki portu yeterince ayırıyor. Referans CLI/config/capability ile mevcut offline kodun destek iddiası korunuyor; yeni alan veya runtime API uygulanmadı. Araç mimarisindeki eksen tablosuna EVREN hizmeti de açıkça eklendi.

Standartların hata, güvenlik, performans ve test gerekleri doğru yönde; canlı hesap ve dayanıklılık işleri tamamlandı sayılmıyor. Uygulama yokken bütün standartları yeniden yazmak yerine, kartın hangi gereği hangi test/ölçümle karşılayacağı zorunlu oldu. Doğrulama seçimi CONTRIBUTING'de tek yerde; skill'ler komut kopyalamıyor. Özel güvenlik kanalının B12 yayın kapısı bu belge işiyle etkinleştirilmedi.

## Referans ajan düzenlerinden uyarlama

Kullanıcının seçtiği yerel referanslarda yalnız ortak skill katalogları ve ilgili prosedürler okundu; worktree kopyaları, kullanıcı ayarı/credential ve çalışma hafızası girdi yapılmadı. Bu kaynaklar başka checkout'a çalışma zamanı bağımlılığı değildir.

| Prosedür grubu | İncelenen ilgili örüntü | Yörünge'ye alınan / alınmayan |
|---|---|---|
| Başlangıç/teslim | start-task, implement-task, commit-and-pr, review/katalog yönlendirmesi | Plan ile uygulamayı ve küçük düzeltmeyi ayırma. Başka ürünün modülleri, kendi main/commit/izin kuralları alınmadı. |
| Sözleşme/doğrulama | config alanı, test, PR review ve release rehberi | Şema → tüketici → anlamlı test → belge izi; kurulu artefaktın import kökeni. Eğitim bağımlılığı, çift dil, kendi coverage eşiği ve yayın komutları alınmadı. |
| Bağlam/inceleme | scoped task/implement/review, ilgili sınırları okuma ve reviewer rolü | Kanonik sözleşme ve dar bağlam; severity/etki/kanıtlı bulgu. Başka ürünün stack/engine kuralları, sabit model ve her değişiklik için onay kapısı alınmadı. |
| İş kartı/kural ayrımı | görev kartı, code/approval review, skill/kural ayrımı | Kabul iddiasını kanıtla karşılaştırma, yakın kartın durumu ve istemciden bağımsız katalog. Başka ürünün dil/donanım sınırları ve bağımsız ajan zorunluluğu alınmadı. |

Metinler Yörünge için yazıldı; referans proje talimatları bu depoda yürütülmedi. Codex repo discovery için [resmî OpenAI skills](https://learn.chatgpt.com/docs/build-skills), Claude project/symlink davranışı için [resmî Claude Code skills](https://code.claude.com/docs/en/skills) okundu (2026-10-27). `.agents/skills` kanonik; Claude'a kişi/global ayarı değiştirmeden göreli alias sağlanıyor.

## Doğrulama ve pratik sınama

- Altı skill `skill-creator` quick validator'ından geçti; proje helper'ı metadata/UI prompt, alias ve bir hazır kartı doğruladı.
- Toplam 128 offline test geçti. Yeni 28 senaryo; duplicate/yanlış metadata, yanlış UI, kopya/absolute/dış alias, bilinmeyen veya tamamlanmamış bağımlılık, yanlış capability, durum drift'i, bölünmemiş L iş ve kaynak sınırını kapsıyor. Başlanmış/tamamlanmış işin bağımlılığı, boş/eksik kart gövdesi, verified teslim kaydı ve çakışan faz ID'leri de sınandı; bağımsız hata nedenlerini maskeleyen üç negatif fixture düzeltildi. Kod örneklerinin gerçek anchor sayılmaması da sınandı.
- Ruff format/lint ve strict mypy temiz. Açık kaynak listesinde 85 Markdown dosyası, link/fence/anchor ve git diff kontrolü geçti. Wheel/sdist build ve ikisinin ayrı temiz kurulum/import-konsol deneyi başarılı. Wheel 17 runtime/metadata üyesiyle kaldı; kanonik ajan rehberleri yalnız sdist geliştirme girdisinde, Claude alias symlink'leri dağıtım dışında. Arşiv kimliği/SHA-256 ve sonuçlar build sonrası `dist/verification.jsonl` kaydındadır; bu kaynak belgenin kendi hash'i içine yazılmaz.
- Skill kullanım senaryoları içerik üzerinden kontrol edildi: plan-only istek kod başlatmıyor; ready kartı uygula talebi planla bırakılmıyor; yalnız review dış yazma yapmıyor; doğrulama canlı hesaba geçmiyor; PR akışı Master/release yetkisi üretmiyor. Bunlar yazarın senaryo incelemesidir, bağımsız model/istemci forward-test'i değildir.
- Codex/Claude UI'sında doğal dil otomatik seçim ve yeni oturum discovery e2e testi yapılmadı; dosya/metadata/alias yapısı ve resmî yerleşim doğrulandı. Mermaid görsel render ve canlı EVREN/GPU testi yapılmadı.
- Tam geliştirme/test checkout'u gerçek symlink destekleyen macOS/Linux ile sınırlıdır; Windows checkout davranışı doğrulanmadı. Kart helper'ı yapısal alan/kanıt varlığını kontrol eder; kabulün gerçekten sağlanması review konusudur. Güncel durum indeks/current içinde tekrar edilmez; kart metadata'sı ve onunla denetlenen faz satırı kullanılır.

## Hazırlık kararı ve kalan işler

[P01-2a](../roadmap/tasks/p01-2a-secret-resolution.md) bağımsız, kabulü belirli ve `ready`; implementasyonu bu review'ye dahil değil. Sonraki state/credential nesli işi B02/B13 kararı ve P01-4a temelinden sonra hazır edilir. P02/P03 için resmî sözleşme, SDK/aday sürümü ve yetkili küçük pilot; public release için B11 kapsam/sürüm ve B12 kanal kapısı açık kalır. Bu ayrım roadmap eksikliğini gizlemek değil, henüz kanıtı olmayan geleceği `ready` saymamaktır.

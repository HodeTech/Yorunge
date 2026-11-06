# P02-3 uygulama öncesi belge, kod ve kaynak incelemesi

**Tarih:** 2026-11-06 Europe/Istanbul. **Dal/taban:** `feat/p02-3-dataset-recovery`, development `94aaaf0`; hazırlık `9e9f3df` kapanış commit’inin üzerindedir. **Durum:** ADR-0031/0032/0033 Proposed, kullanıcı onayı bekleniyor; ürün kodu başlamadı. Bu kayıt uygulama veya canlı kabul değildir.

## Yöntem ve incelenen belgeler

AGENTS/ajan rehberi; current, roadmap, P02 fazı ve P02-2 teslim planı; ADR-0011–0018, 0020–0030; transfer, v2, uzlaştırma, workflow, public, consumer, HTTP ve manifest referansları; P02-2a/b/c/s kartları ve kabul kaydı; datasets/artifacts/catalog modülleri, mimari veri belgesi, güvenlik/UX/test/performans/belgeleme/kanıt standartları; ürün kapsamı, yetenek matrisi, user-journeys, CLI ve local-state sözleşmeleri; P02-0a SDK/pilot araştırması ve P02-2 hazırlık kaydı tam okundu. Önceki belgelerdeki bütün “P02-3’te” ileri referansları (yaklaşık 25 satır) tek tek çıkarıldı ve kapsama eşlendi: etkili resume P02-3a, indirme/verify P02-3b, sürüm/bölme P02-3c, P03-1 bağımlılığı P02-3c, ortak indirme tüketicisi P02-4b.

İki bağımsız, salt okunur keşif ajanı (yükleme durum makinesi ve indirme/dosya ilkelleri) mevcut kodu `9e9f3df` üzerinde haritaladı; ana inceleme ayrıca 4 Kasım keşfinden yerelde üretilmiş (repoda olmayan) gözleme dayalı Platform OpenAPI belgesini ve kamu web istemci varlıklarını (yalnız metin; yürütülmedi) okudu. **Bu turda 0 hesap isteği, 0 etkili istek** yapıldı; Platform bilgisi 4 Kasım 2026 tek hesap gözlemidir ve kalıcı sözleşme değildir. Ham keşif kayıtları repoda değildir; burada yalnız şema düzeyinde özet ve kamu varlık kimlikleri yer alır.

## Doğrulanmış hazırlık boşlukları ve aksiyonlar

| Bulgu | Kanıt | Aksiyon |
|---|---|---|
| Etkili resume için mevcut modeli gevşetmek güvenli değildir | Write lease `fence=1` ve tek write owner dört bağımsız kapıda (kayıt doğrulayıcısı, repository alan eşitliği, intent bağı, bellek-içi write access); makbuz mevcut intent, aynı write owner ve intent penceresi ister | ADR-0031: aynı operation’ı canlandırmak yerine soy bağlı yeni, onaylı continuation |
| Gözlem makbuzu ADR-0026 hükümleriyle çelişir | “Metadata makbuzu tamamlamaz”; intent’i olmayan aşamaya makbuz yazılamaz (DDL FK) | ADR-0031: gözlem yalnız continuation sınıflandırmasında kullanılır, grafiğe makbuz eklenmez |
| Plan/onay/transfer penceresi 900 s | Kaynak plan kesintiden sonra geçersiz (`upload_plan_not_valid`); yeni onay yalnız operation’sız plana verilir | ADR-0031: continuation kendi 900 s penceresi ve fresh onayıyla çalışır |
| Alt küme Manifest’i mevcut capture’a sığmaz | Capture bütün root’u tarayıp `observed == expected` ister; alt küme `input_changed` verir | ADR-0031: tam Manifest/kök bağlı kalır, yalnız `file_indices` gönderilir |
| Dataset öğesi baytları API anahtarıyla indirilemez | `file_url` aynı API origin’inde imzasız yol; API anahtarıyla 401 “Oturum gerekli”; web istemcisi oturum JWT’si ekler; öğe başına bayt rotası yok | ADR-0032: dataset indirme kurulmaz, [P02-R5](../roadmap/tasks/p02-r5-dataset-item-byte-access.md) blocked; faz kabulü 1. madde `partial` kayıtlı |
| Model ağırlığı imzalı URL ile API anahtarıyla alınabilir görünüyor | `models/versions/{id}/download` JSON `download_url`; istemci URL’yi başlıksız tarayıcı gezinmesiyle açar | ADR-0032: kesin sürüm kimliğiyle ilk tüketici (P02-3n); canlı doğrulama kullanıcı yetkisine bağlı |
| Mevcut ağ/dosya ilkelleri indirme için yetersiz | Storage portu yalnız PUT/64 KiB yanıt; hizmet HTTP yolu imzalı query’yi yeniden kodlar ve guard’sızdır; akışlı yazıcı, sidecar, Range/ETag yorumu, doğrulama sonucu yok | ADR-0032: private `DownloadTarget`/GET taşıması, sink/publisher, doğrulama sözlüğü |
| Sürüm/bölme için tip ve referans yok; üyelik listesi sağlayıcıda yok | Sürüm gövdesi yalnız sayı ve etiket anlık görüntüsü; `version_tag` ile adresleme; tag yeniden kullanımı farklı `id` | ADR-0033: salt okuma, sürüm kimliği + etiket + sayı bağı, üyelik iddiası yok; freeze P02-R4 |
| P02-3c’nin P02-3a/b bağımlılığı teknik değil | Sürüm okuma ortak HTTP/credential altyapısıyla çalışır | Faz tablosunda teknik bağımlılık `P02-0d`; plan sırası sonradır |
| Belge/kod uyumsuzlukları | `http-transport.md` “streaming upload yoktur” der, oysa private storage portu PUT akıtır; ADR-0024 genel durum listesinde `planned` var, kodda yok | `http-transport.md` düzeltildi; ADR-0024’e düzeltme notu eklendi |

## Kod gözlemleri

`9e9f3df` kaynağında, kanıtlı kısaltılmış özet (ayrıntılı dosya:satır haritası ajan raporunda; kod değişimlerinde yeniden doğrulanır):

- **Restart bugünkü sınırı.** Public `start` mevcut operation’ı yeniden yürütmez; latched ve running/unknown/admitted ise `operation_uncertain`/5. `reconcile` yerel öncelik sırasında terminal, baseline, etkin lease ve policy bayrağını network öncesi uygular; latched ama dataset kimliği olmayan veya graf eksik kayıt `cleanup_expired` ile `unknown`/`request_uncertain` olur. Restart’ın terminale giden tek yolu bütün 2+3N makbuzun var olduğu durumdur. Gerçek SIGKILL sınırları sekiz noktadır (admission, create intent/response/commit, PUT response, confirm commit, proof before/after commit); **link** ve **iki-worker PUT** için gerçek-kill testi yoktur.
- **Tek-attempt kapıları.** Write lease `fence==1` ve owner eşitliği dört yerde; `workflow_latched` yalnız tek yönlü; plan başına tek operation DDL `UNIQUE`; namespace `create_operation_id UNIQUE` ve Python kontrolü; rezervasyon formülü her kayıt okumasında doğrulanır; kapasite 128/128/4.096/16 MiB; global expiry sınırı 13.696; reset parmak izi ve yedek allowlist’i her payload’ı hash’ler/tanır.
- **2+3N bağlaşıklığı.** Gerekli aşamalar, kabul edilmiş aşama kümesi, öncül zinciri, istek-limit tipleri (`max_create: Literal[1]`), rezerv formülü, doğrulama toplamı, koordinatör döngüleri ve items okuyucusu `file_count`/create-ilk varsayımını taşır; `decode_versioned` iki tip imzalıdır. Yeni sürüm DDL gerektirmez; eski binary yeni satırı `state_invalid` ile reddeder (ADR-0026 emsali).
- **Salt okuma uzlaştırma yeniden kullanılabilir parçaları.** Context/owned/detail/üyelik okuması ve sayfalı items okuyucusu sınıflandırıcı için yeterlidir; items toplamı uyuşmazlığında hata fırlatan indirgeyici sınıf kümesi döndürmez (yeni kardeş indirgeyici gerekir).
- **Ağ.** Guarded transfer oturumu (public-IP, pinned peer, iki slot) yöntem/başlık bağımsızdır; mevcut test aynı origin’de kimliksiz doğrudan isteğin kimlikli GET’ten sonra `X-API-Key` taşımadığını gösterir. Eksik olan tipli GET girişi, Range/ETag yorumu ve 200/206/416 ayrımıdır. Slot paylaşımı: tek akış tek slot tutar.
- **Dosya.** Akışlı yazıcı, sidecar, resume durumu yoktur; manifest yayıncısı (stage → fsync → exclusive link → kimlik kontrolü) kalıp olarak uygundur fakat bellekteki 8 MiB bayta, `DatasetTree` ve `manifest_*` kodlarına bağlıdır. Ham akış ölçümü diske yazmaz; indirme için kanıt doğrulayıcısı yoktur.

## Platform gözlemleri ve sınırları

| Konu | Gözlem (4 Kasım 2026, tek hesap) | Sınır |
|---|---|---|
| Öğe baytı | `file_url` API anahtarıyla 401; web istemcisi Bearer oturum JWT’si ekler ([`useAuthBlob`](https://evren.ssyz.org.tr/assets/useAuthBlob-BPCjZfCs.js) 1.399 byte, SHA-256 `b20f1f11…bf94b`, [`AuthImage`](https://evren.ssyz.org.tr/assets/AuthImage-nQftWiMy.js) 1.116 byte, SHA-256 `c8f950e2…7af24`) | Tek örnek; JWT/çerez denenmedi; sunucu davranışı garantisi değil |
| Model ağırlığı | `GET models/versions/{id}/download?format=` API anahtarıyla JSON `{download_url, filename}`; istemci URL’yi başlıksız açar ([`ModelDetailPage`](https://evren.ssyz.org.tr/assets/ModelDetailPage-C-bw6r8v.js) 66.951 byte, SHA-256 `899a5737…d677d`); örnek URL aynı API origin’inde imzalı query | Hesapta model olmadığından canlı imzalı GET gözlenmedi; ETag/Range/ücret/lisans bilinmiyor |
| Export | `export/download` (ZIP), `versions/{tag}/export`, `…/export-url` API anahtarını kabul etti | Hazırlık/ücret ve ZIP işleme ayrı karar; ilk tüketici değil |
| Sürümler | Liste (sayfalı), detay (`id`, `version_tag`, `is_frozen`, `is_partial`, `item_count`, `split_config`, sınıf etiketi anlık görüntüsü) ve bölme sayımı API anahtarıyla okunur ([`datasetApi`](https://evren.ssyz.org.tr/assets/datasetApi-DZyifXpy.js) 7.005 byte, SHA-256 `79387e65…a16b`); üye listesi yok; etiket yeniden kullanımı farklı `id` | Immutable garanti değil; oluşturma 500 gözlemleri |
| Confirm/dedup | Confirm hiç PUT edilmemiş nesne için de 201 ve `ready` item yaratır; aynı SHA-256’lı üçüncü dosya `created=0/batch_duplicates=1` (r4) | Tek örnek; idempotency/request-correlation yok |

## Kullanıcıya sunulan kararlar ve gereken dış bilgi

[Teslim planı](../roadmap/p02-3-delivery-plan.md#kullanıcı-kararları) ADR-0031/0032/0033 onaylarını, ilk indirme tüketicisi ve dataset bayt erişimi kararını, freeze/sahiplenme ertelemelerini, tek PR sınırını ve canlı kabul yetkilerini listeler. Yeni ADR onayı olmadan bağımlı ürün kodu başlamaz; onay, sağlayıcı sözleşmesini, ücretini veya yetkisini kanıtlamaz.

## Review ve doğrulama kaydı

Ana inceleme ve iki salt okunur keşif tamamlandı. Yeni yazılmış ADR/referans/kart/plan metinlerinin iki fresh belge review turu aşağıda gerçek sonuçlarıyla kaydedilir; bu tur tamamlanmadan kullanıcı onayına gidilmez.

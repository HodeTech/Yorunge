# ADR-0003: Hafif modüler Python çekirdeği

**Durum:** Accepted — başlangıç tasarımı. **Tarih:** 2026-10-27.

## Bağlam

EVREN istemcileri ve eğitim araçları Python ekosisteminde bulunuyor. Kullanıcının hızlı başlangıç, kullanım kolaylığı ve kaynak verimliliği öncelikleri, temel API istemcisinin büyük ML ortamına bağlı olmamasını gerektiriyor.

## Karar

Python 3.11+ hedefleyen tek modüler dağıtım tasarlanır. Domain/kullanım senaryoları, hizmet/araç/execution adaptörleri ve kullanıcı yüzeyi ayrıdır. Eğitim araçları ayrı ortam/isteğe bağlı entegrasyondur. Kesin CLI/HTTP/şema paketleri [teknoloji belgesindeki](../tech-stack.md) P01 deneyleriyle seçilir.

## Alternatifler

Başlangıçta mikroservis ve uzak kontrol düzlemi yerel görevleri gereksiz karmaşıklaştırır. Go/Rust ile hafif binary seçeneği dağıtım avantajı taşır; fakat Python araçları/SDK'lar için ek köprü maliyeti getirir. İlk ürün için Python entegrasyon ve teslim hızını kolaylaştırır; başlangıç maliyeti lazy import ve ölçümle kontrol edilir.

## Sonuçlar

Tek dil tercihinin düşük başlangıç gecikmesini kendiliğinden sağlamadığı kabul edilir. Ağır import ve kurulum bütçeleri ölçülür. Başka dilde worker ancak ölçülmüş darboğaz/dağıtım ihtiyacıyla ayrıca ele alınır. Bugün paket veya uyum matrisi kurulmuş değildir.

# Changelog

## 1.0.0 — 2026-09-21

Primeira versão distribuída.

- Transcrição de texto manuscrito (Google Cloud Vision; TrOCR offline para palavra única; modo offline automático com a própria CNN para letras).
- Avaliador híbrido: legibilidade por CNN MobileNetV2 (26 letras do EMNIST, 93,9 % de acurácia, calibrada) + cinco medidas geométricas contra moldes de letra de forma; nota 0–100 por letra com motivo.
- Módulo de prática: letras, palavras por fases, quiz, dicionário; letra-guia; mapa de diferenças entre o traço e o molde após cada tentativa.
- Progresso sincronizado no Firebase, histórico de notas e gráfico de evolução (aplicativo e site).
- Segmentação robusta: linhas de pauta, letras encostadas e fragmentos de traço.
- `config.json` para limiares e pesos; `calligraphos.log`; tela Sobre com métricas do modelo; testes automatizados em CI.
- Site complementar (React) reorganizado em abas, instalável como PWA.

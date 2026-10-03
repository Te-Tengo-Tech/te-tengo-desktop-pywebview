# 0003. MediaPipe 0.10.35 en un proceso aparte

**Estado:** aceptada (2026-10-03)

## Contexto
- La estimación de pose es intensiva en CPU (la EC2 t3.small no tiene GPU). Esperarla dentro de una ruta `async`, o mandarla a un hilo, no ayuda por el GIL; hay que usar otro proceso (Zhanymkanov, s.f.).
- MediaPipe 1.0.1 falla al construir el grafo en macOS con CPU (google-ai-edge/mediapipe#6356). La 0.10.35 funciona y tiene instaladores para Linux x86_64 y Windows.

## Decisión
- Fijar `mediapipe==0.10.35` y Python 3.11.
- Ejecutar el Pose Landmarker (modelo *lite*) en un `ProcessPoolExecutor` con un solo proceso, que crea el modelo una vez al iniciar.
- Usar el modo `IMAGE`: cada fotograma es independiente, así que tolera las reconexiones del agente sin exigir marcas de tiempo crecientes como el modo `VIDEO`.

## Consecuencias
- El WebSocket sigue recibiendo mientras se infiere.
- El modo `IMAGE` no usa el seguimiento entre fotogramas. Si la precisión lo requiere, se evaluará el modo `VIDEO` con un landmarker por cámara.
- Para actualizar MediaPipe hay que comprobar antes que el bug de macOS esté resuelto.

Google AI Edge. (2026). *Tasks Vision graphs with TensorsToDetectionsCalculator abort at graph build on macOS CPU* (Issue 6356). GitHub. https://github.com/google-ai-edge/mediapipe/issues/6356
Zhanymkanov, Y. (s.f.). *FastAPI best practices: CPU intensive tasks*. https://github.com/zhanymkanov/fastapi-best-practices

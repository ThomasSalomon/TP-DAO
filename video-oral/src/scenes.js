export const WIDTH = 1920;
export const HEIGHT = 1080;
export const FPS = 30;
export const DURATION = 8 * 60;
export const ENTRY_FRAMES = 8;
export const MIN_HOLD_FRAMES = FPS * 3;

const page = (seconds, name, blocks, motion) => ({ seconds, name, blocks, motion });
const rows = (block, first, last) => ({ block, first, last });

export const chapters = [
  {
    id: 'inicio', view: 'Negocio', name: 'Apertura e índice', start: 0,
    cue: '¿Cuándo se puede vender la mercadería que ya llegó al local? Sigamos un bulto para ver dónde se habilita.',
    pausePage: 2,
    pages: [page(8, 'Portada', ['cover']), page(8, 'Índice y enfoque de Negocio', ['agenda'])],
  },
  {
    id: 'n-dominio', view: 'Negocio', name: 'Dominio', start: 16,
    cue: 'Sigan la mercadería desde la compra al CD hasta la venta, con los movimientos del inventario y de caja.',
    pausePage: 2,
    pages: [
      page(6, 'El problema del negocio', [1]),
      page(9, 'Vida de una unidad de mercadería', [2], { boxes: [0, 1, 2, 3, 4, 5], token: true }),
      page(7, 'Flujo del negocio', [3, 4], { boxes: [0, 1, 2, 3, 4, 5, 6, 7] }),
      page(6, 'Entidades principales', [5, 6]),
    ],
  },
  {
    id: 'n-reglas', view: 'Negocio', name: 'Reglas de negocio', start: 44,
    cue: 'Las cinco primeras reglas vienen del enunciado. Python aplica cada validación en el objeto que conoce ese dato.',
    pausePage: 1,
    pages: [
      page(7, 'Reglas del enunciado', [1, rows(2, 1, 5)]),
      page(7, 'Reglas adicionales, primera parte', [rows(2, 6, 10)]),
      page(6, 'Reglas adicionales, segunda parte', [rows(2, 11, 14)]),
      page(6, 'Dónde se controlan las reglas', [3]),
    ],
  },
  {
    id: 'n-ciclo', view: 'Negocio', name: 'Ciclo de vida del bulto', start: 70,
    cue: 'Cuando el bulto queda verificado, el saldo sigue pendiente. La verificación del remito lo habilita para venta.',
    pausePage: 2,
    pages: [
      page(5, 'Respuesta corta sobre el bulto', [1]),
      page(10, 'Recorrido normal y doble verificación', [2], {
        boxes: [0, 1, 2, 3, 4, { x: 410, y: 285, width: 324, height: 25 }],
        edges: [0, 1, 2, 3, 4, 7], token: true,
      }),
      page(5, 'Recepción con precinto roto o distinto', [2], {
        boxes: [2, 5], edges: [6], color: 'bad',
      }),
      page(4, 'Stock desde la preparación hasta el despacho', [3, rows(4, 1, 4)]),
      page(4, 'Stock en recepción y verificaciones', [rows(4, 5, 8)]),
      page(6, 'Doble control, historial y mercadería en custodia', [5, 6, 7]),
    ],
  },
  {
    id: 'n-patrones', view: 'Negocio', name: 'Por qué elegimos cada patrón', start: 104,
    cue: 'State decide qué puede hacer el bulto ahora. Strategy deja que el usuario elija cómo agrupar el mismo reporte.',
    pausePage: 1,
    pages: [page(15, 'Decisiones de State y Strategy', [1]), page(8, 'Comparación y otros patrones', [2, 3, 4])],
  },
  {
    id: 'n-reportes', view: 'Negocio', name: 'Reportes', start: 127,
    cue: 'Muestren qué pregunta responde cada reporte y cómo los filtros cambian el resultado que se consulta.',
    pausePage: 1,
    pages: [page(10, 'R-01 a R-04 y sus filtros', [1]), page(8, 'Criterios de cálculo y presentación', [2])],
  },
  {
    id: 'n-roles', view: 'Negocio', name: 'Roles de usuario', start: 145,
    cue: 'Señalen quién interviene en cada operación y expliquen cómo se agregarían cuentas y permisos si hicieran falta.',
    pausePage: 2,
    pages: [
      page(5, 'Alcance de usuarios y permisos', [1]),
      page(8, 'Actores y responsabilidades', [2], { boxes: [0, 1, 2, 3, 4] }),
      page(5, 'Cómo se agregarían usuarios', [3]),
    ],
  },
  {
    id: 'n-librerias', view: 'Negocio', name: '¿Usamos librerías?', start: 163,
    cue: 'Las clases, reglas y cálculos están en Python. Identifiquen qué herramientas se usan en HTTP, pantalla, datos y pruebas.',
    pausePage: 2,
    pages: [
      page(5, 'Lógica del negocio y herramientas', [1]),
      page(7, 'Librerías, usos y tipos', [2]),
      page(5, 'Preguntas sobre ORM y reportes', [3, 4]),
    ],
  },
  {
    id: 'tecnica', view: 'Técnica', name: 'Índice', start: 180,
    cue: 'Ahora seguimos una venta por dentro del sistema y volvemos al bulto para ver las clases, el código y los patrones.',
    pausePage: 1,
    pages: [page(8, 'Índice y enfoque de Técnica', ['agenda'])],
  },
  {
    id: 'arq', view: 'Técnica', name: 'Cómo está armado', start: 188,
    cue: 'Sigan una venta desde el formulario hasta SQLite. El dominio valida y la pantalla muestra la confirmación de la API.',
    pausePage: 1,
    pages: [
      page(8, 'Capas del sistema', [1, 2], { boxes: [0, 1, 2, 3], token: true }),
      page(6, 'Ejemplo de registrar una venta', [3, 4]),
      page(6, 'Presentación y envío de JSON', [5, 6]),
      page(6, 'Adaptador HTTP y mensajes de dominio', [7, 8]),
      page(6, 'Dominio y objetos validados', [9, 10]),
      page(6, 'Persistencia y confirmación 201', [11, 12]),
    ],
  },
  {
    id: 'dominio', view: 'Técnica', name: 'Dominio y entidades', start: 226,
    cue: 'Venta crea sus propias partes. Una NecesidadReposicion ya existe cuando llega a la orden. Señalen la diferencia en el diagrama y en los constructores.',
    pausePage: 5,
    pages: [
      page(5, 'Resumen del dominio', [1]),
      page(6, 'Entidades por módulo, primera parte', [2, rows(3, 1, 5)]),
      page(5, 'Entidades por módulo y registros', [rows(3, 6, 9), 4]),
      page(5, 'Criterio de composición y agregación', [5, 6]),
      page(13, 'Composición, agregación y cardinalidades', [7], { boxes: [0, 8, 15] }),
      page(8, 'Composición de Venta', [8, 9]),
      page(6, 'Composición de Bulto', [10]),
      page(8, 'Agregación de NecesidadReposicion', [11]),
      page(7, 'Referencias en Python y encapsulamiento', [12, 13, 14]),
      page(7, 'Ubicación de las validaciones', [15, 16]),
      page(6, 'Ubicaciones y stock', [17, 18]),
    ],
  },
  {
    id: 'patrones', view: 'Técnica', name: 'Patrones de diseño', start: 302,
    cue: 'En State, el bulto delega en el objeto estado. En Strategy, el reporte pide una clave a la estrategia que seleccionó la API.',
    pausePage: 4,
    pages: [
      page(5, 'Contratos comunes y problema de State', [1, 2, 3]),
      page(5, 'Referencias de State, primera parte', [rows(4, 1, 6)]),
      page(5, 'Referencias de State, segunda parte', [rows(4, 7, 11)]),
      page(8, 'Estructura de State', [5], { boxes: [0, 1, 3, 4, 5, 6] }),
      page(7, 'Delegación y cambio de estado en código', [6]),
      page(6, 'La referencia al contexto y las transiciones', [7]),
      page(4, 'Problema de Strategy en R-01', [8, 9]),
      page(5, 'Referencias de Strategy, primera parte', [rows(10, 1, 5)]),
      page(4, 'Referencias de Strategy, segunda parte', [rows(10, 6, 9)]),
      page(7, 'Estructura de Strategy', [11], { boxes: [0, 1, 2, 3, 4, 5] }),
      page(5, 'Uso de la estrategia en ReporteVentas', [12, 13]),
      page(5, 'Comparación y otros patrones', [14, 15, 16]),
    ],
  },
  {
    id: 'tx', view: 'Técnica', name: 'Transacción', start: 368,
    cue: 'Venta, stock y caja se confirman juntos. Si falla el guardado, se revierte lo pendiente y se vuelve al último estado confirmado.',
    pausePage: 1,
    pages: [
      page(7, 'Ramas de commit y rollback', [1, 2], { boxes: [0, 1, 2, 3, 4], edges: [0, 1, 2, 3, 4] }),
      page(6, 'Transacción SQLite y recuperación de memoria', [3]),
      page(7, 'Secuencia de una venta', [4, 5], { boxes: [0, 1, 2, 3, 4], edges: [0, 1, 2, 3] }),
      page(5, 'SQL parametrizado, reintentos y concurrencia', [6]),
    ],
  },
  {
    id: 'ciclo', view: 'Técnica', name: 'Ciclo de vida del bulto', start: 393,
    cue: 'Muestren dónde se registra la transición y qué llamada habilita el stock cuando se verifica el remito.',
    pausePage: 5,
    pages: [
      page(5, 'Resumen técnico del bulto', [1]),
      page(7, 'Estados, terminales y transición rechazada', [2], {
        boxes: [0, 1, 2, 3, 4, 5, 6], edges: [0, 1, 2, 3, 4, 5, 6, 7],
      }),
      page(5, 'Estados y saldos antes de la recepción', [3, rows(4, 1, 4)]),
      page(4, 'Estados y saldos en recepción y verificación', [rows(4, 5, 8)]),
      page(4, 'Doble verificación en código', [5, 6]),
      page(5, 'Trazabilidad, rechazo y estado del remito', [7, 8, 9, 10]),
    ],
  },
  {
    id: 'reportes', view: 'Técnica', name: 'Reportes', start: 423,
    cue: 'Sigan R-01 desde los filtros hasta el JSON y señalen dónde se agrupan y suman los movimientos de caja.',
    pausePage: 3,
    pages: [
      page(4, 'Cálculo y exposición de los reportes', [1]),
      page(6, 'Endpoints y código de R-01 a R-04', [2]),
      page(5, 'Flujo de R-01', [3, 4], { boxes: [0, 1, 2, 3, 4], token: true }),
      page(4, 'Importes, objetos de resultado y pruebas', [5]),
    ],
  },
  {
    id: 'abc', view: 'Técnica', name: '¿Por qué usamos @abstractmethod?', start: 442,
    cue: 'Recorran los dos casos que fallan al instanciar y muestren cómo PorDia cumple el contrato común.',
    pausePage: 2,
    pages: [
      page(5, 'Por qué se usa una clase abstracta', [1]),
      page(6, 'Qué permite y qué impide ABC', [2], { boxes: [0, 1, 2, 3] }),
      page(5, 'EstadoBulto y EstrategiaAgrupacion en código', [3]),
      page(5, 'Polimorfismo, métodos concretos y super()', [4, 5, 6]),
    ],
  },
  {
    id: 'librerias', view: 'Técnica', name: 'Librerías y dependencias', start: 463,
    cue: 'Cierren ubicando las dependencias externas y los módulos estándar en las capas en que se usan.',
    pausePage: 2,
    pages: [
      page(4, 'Biblioteca estándar en el dominio', [1]),
      page(4, 'Dependencias y versiones', [2]),
      page(5, 'Módulos estándar de Python', [3, 4]),
      page(4, 'Alcance de las dependencias del TP', [5]),
    ],
  },
];

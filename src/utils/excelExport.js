/**
 * excelExport - Утилиты для экспорта данных в Excel
 * 
 * Назначение: Генерация профессионально оформленных Excel-файлов с данными оценок
 * Используется в: AdminEvaluationsMatrix
 * 
 * Библиотека: xlsx-js-style (форк xlsx с поддержкой стилей)
 */

import * as XLSX from 'xlsx-js-style';
import { groupCriteria, getCriterionFinalScore, getCLevelChannel } from './matrixUtils';

// ============================================
// СТИЛИ
// ============================================

const COLORS = {
  primary: '4F46E5',      // Indigo - основной
  primaryLight: 'E0E7FF', // Светло-индиго
  header: '1E3A5F',       // Темно-синий для заголовков
  headerText: 'FFFFFF',   // Белый текст
  subHeader: 'F1F5F9',    // Светло-серый подзаголовок
  self: 'DBEAFE',         // Голубой - самооценка
  general: 'D1FAE5',      // Зеленый - общие
  project: 'E9D5FF',      // Фиолетовый - проектные
  management: 'CCFBF1',   // Бирюзовый - руководство
  clevel: 'FED7AA',       // Оранжевый - c-level
  total: 'FEF3C7',        // Желтый - итого
  altRow: 'F8FAFC',       // Альтернативная строка
  border: 'CBD5E1',       // Цвет границ
};

const FONTS = {
  title: { name: 'Calibri', sz: 16, bold: true, color: { rgb: COLORS.header } },
  subtitle: { name: 'Calibri', sz: 11, color: { rgb: '64748B' } },
  header: { name: 'Calibri', sz: 10, bold: true, color: { rgb: COLORS.headerText } },
  subHeader: { name: 'Calibri', sz: 9, bold: true, color: { rgb: '374151' } },
  cell: { name: 'Calibri', sz: 10, color: { rgb: '1F2937' } },
  number: { name: 'Calibri', sz: 10, color: { rgb: '1F2937' } },
  legend: { name: 'Calibri', sz: 10, color: { rgb: '4B5563' } },
};

const BORDERS = {
  thin: {
    top: { style: 'thin', color: { rgb: COLORS.border } },
    bottom: { style: 'thin', color: { rgb: COLORS.border } },
    left: { style: 'thin', color: { rgb: COLORS.border } },
    right: { style: 'thin', color: { rgb: COLORS.border } },
  },
  medium: {
    top: { style: 'medium', color: { rgb: COLORS.header } },
    bottom: { style: 'medium', color: { rgb: COLORS.header } },
    left: { style: 'medium', color: { rgb: COLORS.header } },
    right: { style: 'medium', color: { rgb: COLORS.header } },
  },
};

const STYLES = {
  title: { font: FONTS.title, alignment: { horizontal: 'left', vertical: 'center' } },
  subtitle: { font: FONTS.subtitle, alignment: { horizontal: 'left', vertical: 'center' } },
  header: { 
    font: FONTS.header, 
    fill: { fgColor: { rgb: COLORS.header } }, 
    alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
    border: BORDERS.thin
  },
  subHeader: { 
    font: FONTS.subHeader, 
    fill: { fgColor: { rgb: COLORS.subHeader } }, 
    alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
    border: BORDERS.thin
  },
  cell: { 
    font: FONTS.cell, 
    alignment: { horizontal: 'left', vertical: 'center' },
    border: BORDERS.thin
  },
  cellCenter: { 
    font: FONTS.cell, 
    alignment: { horizontal: 'center', vertical: 'center' },
    border: BORDERS.thin
  },
  number: { 
    font: FONTS.number, 
    alignment: { horizontal: 'center', vertical: 'center' },
    border: BORDERS.thin,
    numFmt: '0.00'
  },
  numberHighlight: { 
    font: { ...FONTS.number, bold: true }, 
    fill: { fgColor: { rgb: COLORS.total } },
    alignment: { horizontal: 'center', vertical: 'center' },
    border: BORDERS.thin,
    numFmt: '0.00'
  },
};

// Стили для групп критериев
const GROUP_STYLES = {
  'САМООЦЕНКА': { fill: { fgColor: { rgb: COLORS.self } }, font: { ...FONTS.header, color: { rgb: '1E40AF' } } },
  'ОБЩИЕ': { fill: { fgColor: { rgb: COLORS.general } }, font: { ...FONTS.header, color: { rgb: '166534' } } },
  'ПРОЕКТНЫЕ': { fill: { fgColor: { rgb: COLORS.project } }, font: { ...FONTS.header, color: { rgb: '7C3AED' } } },
  'РУКОВОДСТВО': { fill: { fgColor: { rgb: COLORS.management } }, font: { ...FONTS.header, color: { rgb: '0F766E' } } },
  'C-LEVEL': { fill: { fgColor: { rgb: COLORS.clevel } }, font: { ...FONTS.header, color: { rgb: 'C2410C' } } },
  'ИТОГИ': { fill: { fgColor: { rgb: COLORS.total } }, font: { ...FONTS.header, color: { rgb: '92400E' } } },
};

// ============================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ============================================

const getFormattedDate = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}-${String(now.getMinutes()).padStart(2, '0')}`;
};

const safeValue = (value, defaultValue = '') => {
  if (value === null || value === undefined || value === '') return defaultValue;
  return value;
};

const formatScoreForExcel = (score) => {
  if (score === null || score === undefined || score === '') return null;
  const num = typeof score === 'string' ? parseFloat(score) : score;
  return isNaN(num) ? null : parseFloat(num.toFixed(2));
};

// Применить стиль к ячейке
const applyStyle = (ws, cellRef, style) => {
  if (!ws[cellRef]) ws[cellRef] = { v: '' };
  ws[cellRef].s = style;
};

// Создать ячейку со стилем
const styledCell = (value, style) => {
  const cell = { v: value, s: style };
  if (typeof value === 'number') {
    cell.t = 'n';
  } else if (value === null || value === undefined) {
    cell.v = '';
    cell.t = 's';
  } else {
    cell.t = 's';
  }
  return cell;
};

// Получить адрес ячейки
const cellAddr = (r, c) => XLSX.utils.encode_cell({ r, c });

// ============================================
// ГЛАВНАЯ ФУНКЦИЯ ЭКСПОРТА
// ============================================

export const exportMatrixToExcel = (employees, filename = 'matrix') => {
  if (!employees || employees.length === 0) {
    alert('Нет данных для экспорта');
    return;
  }

  const workbook = XLSX.utils.book_new();
  workbook.Props = {
    Title: "Матрица оценок сотрудников",
    Subject: "Оценка персонала",
    Author: "Portal Оценки",
    CreatedDate: new Date()
  };

  // Лист 1: Сводка
  const summarySheet = createStyledSummarySheet(employees);
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Сводка');

  // Лист 2: Матрица
  const matrixSheet = createStyledMatrixSheet(employees);
  XLSX.utils.book_append_sheet(workbook, matrixSheet, 'Матрица');

  // Лист 3: Детали
  const detailSheet = createStyledDetailSheet(employees);
  XLSX.utils.book_append_sheet(workbook, detailSheet, 'Детальные оценки');

  // Лист 4: По отделам
  const statsSheet = createStyledDepartmentSheet(employees);
  XLSX.utils.book_append_sheet(workbook, statsSheet, 'Аналитика');

  // Лист 5: Справка
  const legendSheet = createStyledLegendSheet();
  XLSX.utils.book_append_sheet(workbook, legendSheet, 'Справка');

  // Сохранение
  const fullFilename = `${filename}_${getFormattedDate()}.xlsx`;
  XLSX.writeFile(workbook, fullFilename);
  
  return fullFilename;
};

// ============================================
// ЛИСТ 1: СВОДКА
// ============================================

const createStyledSummarySheet = (employees) => {
  const ws = {};
  let row = 0;

  // Заголовок
  ws[cellAddr(row, 0)] = styledCell('ОТЧЕТ ПО ОЦЕНКЕ ПЕРСОНАЛА', STYLES.title);
  row++;
  ws[cellAddr(row, 0)] = styledCell(`Дата формирования: ${new Date().toLocaleString('ru-RU')}`, STYLES.subtitle);
  row++;
  ws[cellAddr(row, 0)] = styledCell(`Всего сотрудников: ${employees.length}`, STYLES.subtitle);
  row += 2;

  // Заголовки таблицы
  const headers = ['№', 'ФИО СОТРУДНИКА', 'ДОЛЖНОСТЬ', 'ОТДЕЛ', 'ГРЕЙД', 'ПРОЕКТ', 'РУКОВОД.', 'САМООЦЕНКА', 'МЕНЕДЖЕР', 'ПОДЧИНЁННЫЕ', 'C-LEVEL', 'ИТОГОВЫЙ БАЛЛ'];
  headers.forEach((h, c) => {
    ws[cellAddr(row, c)] = styledCell(h, STYLES.header);
  });
  row++;

  // Данные
  employees.forEach((emp, idx) => {
    const criteria = emp.criteria || [];
    
    const selfScores = criteria.filter(c => c.self_score != null).map(c => c.self_score);
    const managerScores = criteria.filter(c => c.manager_score != null).map(c => c.manager_score);
    const cLevelScores = criteria.filter(c => (c.c_level_correction != null) || (c.c_level_score != null)).map(c => c.c_level_correction ?? getCLevelChannel(c).score);
    const subordinateScores = criteria.filter(c => c.subordinate_avg_score != null).map(c => parseFloat(c.subordinate_avg_score));
    
    const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
    const finalScores = criteria.map(c => getCriterionFinalScore(c)).filter(s => s !== null);

    const isAlt = idx % 2 === 1;
    const cellStyle = isAlt ? { ...STYLES.cell, fill: { fgColor: { rgb: COLORS.altRow } } } : STYLES.cell;
    const numStyle = isAlt ? { ...STYLES.number, fill: { fgColor: { rgb: COLORS.altRow } } } : STYLES.number;
    const highlightStyle = STYLES.numberHighlight;

    const rowData = [
      styledCell(idx + 1, { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) }),
      styledCell(safeValue(emp.full_name), cellStyle),
      styledCell(safeValue(emp.job_title), cellStyle),
      styledCell(safeValue(emp.department_name), cellStyle),
      styledCell(safeValue(emp.grade_code), { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) }),
      styledCell(emp.is_project_participant ? 'Да' : 'Нет', { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) }),
      styledCell(emp.has_subordinates ? 'Да' : 'Нет', { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) }),
      styledCell(formatScoreForExcel(avg(selfScores)), numStyle),
      styledCell(formatScoreForExcel(avg(managerScores)), numStyle),
      styledCell(formatScoreForExcel(avg(subordinateScores)), numStyle),
      styledCell(formatScoreForExcel(avg(cLevelScores)), numStyle),
      styledCell(formatScoreForExcel(avg(finalScores)), highlightStyle),
    ];

    rowData.forEach((cell, c) => {
      ws[cellAddr(row, c)] = cell;
    });
    row++;
  });

  // Настройки листа
  ws['!ref'] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: row - 1, c: headers.length - 1 } });
  ws['!cols'] = [
    { wch: 5 }, { wch: 35 }, { wch: 25 }, { wch: 20 }, { wch: 10 },
    { wch: 10 }, { wch: 10 }, { wch: 12 }, { wch: 12 }, { wch: 14 }, { wch: 12 }, { wch: 15 }
  ];
  ws['!rows'] = [{ hpt: 24 }, { hpt: 18 }, { hpt: 18 }, { hpt: 10 }, { hpt: 28 }];

  return ws;
};

// ============================================
// ЛИСТ 2: МАТРИЦА
// ============================================

const createStyledMatrixSheet = (employees) => {
  if (employees.length === 0) {
    const ws = { A1: { v: 'Нет данных', s: STYLES.cell } };
    ws['!ref'] = 'A1';
    return ws;
  }

  const ws = {};
  const merges = [];

  // Собираем критерии
  const allCriteriaMap = new Map();
  employees.forEach(emp => {
    (emp.criteria || []).forEach(c => {
      if (!allCriteriaMap.has(c.criteria_id)) {
        allCriteriaMap.set(c.criteria_id, {
          id: c.criteria_id,
          title: c.criteria_title,
          c_level_only: c.c_level_only,
          selfassesment: c.selfassesment,
          target_audience: c.target_audience
        });
      }
    });
  });

  const sortedCriteria = Array.from(allCriteriaMap.values()).sort((a, b) => {
    const order = (c) => {
      if (c.selfassesment) return 1;
      if (c.c_level_only) return 5;
      if (c.target_audience === 'managers_only') return 4;
      if (c.target_audience === 'project_participants') return 3;
      return 2;
    };
    return order(a) - order(b) || a.id - b.id;
  });

  const getGroupName = (c) => {
    if (c.selfassesment) return 'САМООЦЕНКА';
    if (c.c_level_only) return 'C-LEVEL';
    if (c.target_audience === 'managers_only') return 'РУКОВОДСТВО';
    if (c.target_audience === 'project_participants') return 'ПРОЕКТНЫЕ';
    return 'ОБЩИЕ';
  };

  // Строка 0: Группы
  const fixedCols = 4; // №, ФИО, Отдел, Грейд
  let col = fixedCols;
  let currentGroup = '';
  let groupStart = col;

  // Заполняем служебные ячейки в заголовке (мерджим по вертикали)
  const fixedHeaders = ['№', 'ФИО', 'ОТДЕЛ', 'ГРЕЙД'];
  fixedHeaders.forEach((h, i) => {
    ws[cellAddr(0, i)] = styledCell(h, STYLES.header);
    ws[cellAddr(1, i)] = styledCell('', STYLES.header);
    merges.push({ s: { r: 0, c: i }, e: { r: 1, c: i } });
  });

  // Группы критериев и названия
  sortedCriteria.forEach((crit, idx) => {
    const groupName = getGroupName(crit);
    const groupStyle = GROUP_STYLES[groupName] || STYLES.header;

    if (groupName !== currentGroup) {
      // Закрываем предыдущую группу
      if (currentGroup !== '' && col > groupStart) {
        merges.push({ s: { r: 0, c: groupStart }, e: { r: 0, c: col - 1 } });
      }
      currentGroup = groupName;
      groupStart = col;
    }

    // Строка 0: название группы
    ws[cellAddr(0, col)] = styledCell(groupName, { 
      ...STYLES.header, 
      ...groupStyle,
      alignment: { horizontal: 'center', vertical: 'center' }
    });

    // Строка 1: название критерия
    ws[cellAddr(1, col)] = styledCell(crit.title, { 
      ...STYLES.subHeader,
      fill: { fgColor: { rgb: groupStyle.fill?.fgColor?.rgb || COLORS.subHeader } }
    });

    col++;
  });

  // Закрываем последнюю группу
  if (currentGroup !== '' && col > groupStart) {
    merges.push({ s: { r: 0, c: groupStart }, e: { r: 0, c: col - 1 } });
  }

  // Колонка ИТОГО
  ws[cellAddr(0, col)] = styledCell('ИТОГИ', { ...STYLES.header, ...GROUP_STYLES['ИТОГИ'] });
  ws[cellAddr(1, col)] = styledCell('СРЕДНИЙ БАЛЛ', STYLES.subHeader);
  const totalCol = col;
  col++;

  // Данные сотрудников
  let row = 2;
  employees.forEach((emp, idx) => {
    const isAlt = idx % 2 === 1;
    const cellStyle = isAlt ? { ...STYLES.cell, fill: { fgColor: { rgb: COLORS.altRow } } } : STYLES.cell;
    const numStyle = isAlt ? { ...STYLES.number, fill: { fgColor: { rgb: COLORS.altRow } } } : STYLES.number;

    // Фиксированные колонки
    ws[cellAddr(row, 0)] = styledCell(idx + 1, { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) });
    ws[cellAddr(row, 1)] = styledCell(emp.full_name, cellStyle);
    ws[cellAddr(row, 2)] = styledCell(emp.department_name, cellStyle);
    ws[cellAddr(row, 3)] = styledCell(emp.grade_code, { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) });

    // Критерии
    let totalScore = 0;
    let count = 0;
    let c = fixedCols;

    sortedCriteria.forEach(crit => {
      const found = (emp.criteria || []).find(cr => cr.criteria_id === crit.id);
      const score = found ? getCriterionFinalScore(found) : null;
      ws[cellAddr(row, c)] = styledCell(formatScoreForExcel(score), numStyle);
      if (score !== null) {
        totalScore += score;
        count++;
      }
      c++;
    });

    // Итого
    const avgTotal = count > 0 ? totalScore / count : null;
    ws[cellAddr(row, totalCol)] = styledCell(formatScoreForExcel(avgTotal), STYLES.numberHighlight);

    row++;
  });

  // Настройки листа
  ws['!ref'] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: row - 1, c: col - 1 } });
  ws['!merges'] = merges;
  
  const cols = [{ wch: 5 }, { wch: 30 }, { wch: 18 }, { wch: 10 }];
  sortedCriteria.forEach(() => cols.push({ wch: 14 }));
  cols.push({ wch: 14 });
  ws['!cols'] = cols;

  ws['!rows'] = [{ hpt: 28 }, { hpt: 40 }];

  return ws;
};

// ============================================
// ЛИСТ 3: ДЕТАЛИ
// ============================================

const createStyledDetailSheet = (employees) => {
  const ws = {};
  let row = 0;

  // Заголовок
  ws[cellAddr(row, 0)] = styledCell('ДЕТАЛЬНЫЙ СПИСОК ВСЕХ ОЦЕНОК', STYLES.title);
  row++;
  ws[cellAddr(row, 0)] = styledCell(`Выгружено: ${new Date().toLocaleString('ru-RU')}`, STYLES.subtitle);
  row += 2;

  // Заголовки
  // «C-LEVEL ОЦЕНЩИКОВ» (D-0826-1): колонка C-LEVEL — среднее по всем
  // C-level, поставившим оценку по этому критерию. Без числа оценщиков
  // выгруженная 6 неотличима от чистой 6, хотя может быть средним 4 и 8.
  const headers = ['№', 'СОТРУДНИК', 'ОТДЕЛ', 'ГРУППА', 'КРИТЕРИЙ', 'САМО', 'МЕНЕДЖЕР', 'ПОДЧИН.', 'НАЧАЛЬН.', 'C-LEVEL', 'C-LEVEL ОЦЕНЩИКОВ', 'ИТОГО', 'КОММЕНТАРИЙ'];
  headers.forEach((h, c) => {
    ws[cellAddr(row, c)] = styledCell(h, STYLES.header);
  });
  row++;

  // Данные
  let counter = 1;
  employees.forEach(emp => {
    const grouped = groupCriteria(emp.criteria || []);
    const categories = [
      { name: 'Самооценка', items: grouped.self },
      { name: 'Общие', items: grouped.general },
      { name: 'Проектные', items: grouped.project },
      { name: 'Руководство', items: grouped.management },
      { name: 'C-level', items: grouped.c_level }
    ];

    categories.forEach(cat => {
      cat.items.forEach(c => {
        const isAlt = counter % 2 === 0;
        const cellStyle = isAlt ? { ...STYLES.cell, fill: { fgColor: { rgb: COLORS.altRow } } } : STYLES.cell;
        const numStyle = isAlt ? { ...STYLES.number, fill: { fgColor: { rgb: COLORS.altRow } } } : STYLES.number;

        const rowData = [
          styledCell(counter, { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) }),
          styledCell(emp.full_name, cellStyle),
          styledCell(emp.department_name, cellStyle),
          styledCell(cat.name, { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) }),
          styledCell(c.criteria_title, cellStyle),
          styledCell(formatScoreForExcel(c.self_score), numStyle),
          styledCell(formatScoreForExcel(c.manager_score), numStyle),
          styledCell(formatScoreForExcel(c.subordinate_avg_score), numStyle),
          styledCell(formatScoreForExcel(c.boss_score), numStyle),
          styledCell(formatScoreForExcel(c.c_level_correction ?? getCLevelChannel(c).score), numStyle),
          styledCell(c.c_level_only ? getCLevelChannel(c).count : null, numStyle),
          styledCell(formatScoreForExcel(getCriterionFinalScore(c)), STYLES.numberHighlight),
          styledCell(safeValue(c.comment), cellStyle),
        ];

        rowData.forEach((cell, col) => {
          ws[cellAddr(row, col)] = cell;
        });

        row++;
        counter++;
      });
    });
  });

  ws['!ref'] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: row - 1, c: headers.length - 1 } });
  ws['!cols'] = [
    { wch: 5 }, { wch: 28 }, { wch: 18 }, { wch: 12 }, { wch: 30 },
    { wch: 10 }, { wch: 10 }, { wch: 10 }, { wch: 10 }, { wch: 10 }, { wch: 18 },
    { wch: 10 }, { wch: 35 }
  ];

  return ws;
};

// ============================================
// ЛИСТ 4: АНАЛИТИКА ПО ОТДЕЛАМ
// ============================================

const createStyledDepartmentSheet = (employees) => {
  const ws = {};
  let row = 0;

  ws[cellAddr(row, 0)] = styledCell('АНАЛИТИКА ПО ПОДРАЗДЕЛЕНИЯМ', STYLES.title);
  row += 2;

  // Группируем данные
  const deptData = {};
  employees.forEach(emp => {
    const d = emp.department_name || 'Без отдела';
    if (!deptData[d]) deptData[d] = { count: 0, self: [], manager: [], final: [] };
    deptData[d].count++;
    const crit = emp.criteria || [];
    crit.forEach(c => {
      if (c.self_score != null) deptData[d].self.push(c.self_score);
      if (c.manager_score != null) deptData[d].manager.push(c.manager_score);
      const f = getCriterionFinalScore(c);
      if (f != null) deptData[d].final.push(f);
    });
  });

  // Заголовки
  const headers = ['ОТДЕЛ', 'СОТРУДНИКОВ', 'СР. САМООЦЕНКА', 'СР. МЕНЕДЖЕР', 'СР. ИТОГОВЫЙ', 'МИН. БАЛЛ', 'МАКС. БАЛЛ'];
  headers.forEach((h, c) => {
    ws[cellAddr(row, c)] = styledCell(h, STYLES.header);
  });
  row++;

  // Данные
  const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
  let idx = 0;
  
  Object.entries(deptData).sort((a, b) => a[0].localeCompare(b[0])).forEach(([name, data]) => {
    const isAlt = idx % 2 === 1;
    const cellStyle = isAlt ? { ...STYLES.cell, fill: { fgColor: { rgb: COLORS.altRow } } } : STYLES.cell;
    const numStyle = isAlt ? { ...STYLES.number, fill: { fgColor: { rgb: COLORS.altRow } } } : STYLES.number;

    const rowData = [
      styledCell(name, { ...cellStyle, font: { ...FONTS.cell, bold: true } }),
      styledCell(data.count, { ...STYLES.cellCenter, ...(isAlt ? { fill: { fgColor: { rgb: COLORS.altRow } } } : {}) }),
      styledCell(formatScoreForExcel(avg(data.self)), numStyle),
      styledCell(formatScoreForExcel(avg(data.manager)), numStyle),
      styledCell(formatScoreForExcel(avg(data.final)), STYLES.numberHighlight),
      styledCell(formatScoreForExcel(data.final.length ? Math.min(...data.final) : null), numStyle),
      styledCell(formatScoreForExcel(data.final.length ? Math.max(...data.final) : null), numStyle),
    ];

    rowData.forEach((cell, c) => {
      ws[cellAddr(row, c)] = cell;
    });
    row++;
    idx++;
  });

  // Итого по компании
  row++;
  const allFinal = employees.flatMap(e => (e.criteria || []).map(c => getCriterionFinalScore(c)).filter(s => s !== null));
  const allSelf = employees.flatMap(e => (e.criteria || []).filter(c => c.self_score != null).map(c => c.self_score));
  const allManager = employees.flatMap(e => (e.criteria || []).filter(c => c.manager_score != null).map(c => c.manager_score));

  const totalRowData = [
    styledCell('ИТОГО ПО КОМПАНИИ', { ...STYLES.header, alignment: { horizontal: 'left', vertical: 'center' } }),
    styledCell(employees.length, STYLES.header),
    styledCell(formatScoreForExcel(avg(allSelf)), STYLES.header),
    styledCell(formatScoreForExcel(avg(allManager)), STYLES.header),
    styledCell(formatScoreForExcel(avg(allFinal)), { ...STYLES.header, fill: { fgColor: { rgb: COLORS.total } }, font: { ...FONTS.header, color: { rgb: '92400E' } } }),
    styledCell(formatScoreForExcel(allFinal.length ? Math.min(...allFinal) : null), STYLES.header),
    styledCell(formatScoreForExcel(allFinal.length ? Math.max(...allFinal) : null), STYLES.header),
  ];
  totalRowData.forEach((cell, c) => {
    ws[cellAddr(row, c)] = cell;
  });

  ws['!ref'] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: row, c: headers.length - 1 } });
  ws['!cols'] = [{ wch: 28 }, { wch: 14 }, { wch: 16 }, { wch: 14 }, { wch: 14 }, { wch: 12 }, { wch: 12 }];

  return ws;
};

// ============================================
// ЛИСТ 5: СПРАВКА
// ============================================

const createStyledLegendSheet = () => {
  const ws = {};
  let row = 0;

  ws[cellAddr(row, 0)] = styledCell('СПРАВОЧНАЯ ИНФОРМАЦИЯ', STYLES.title);
  row += 2;

  const items = [
    ['ПОЛЕ', 'ОПИСАНИЕ'],
    ['Самооценка', 'Оценка, которую сотрудник поставил сам себе'],
    ['Оценка менеджера', 'Оценка от непосредственного руководителя'],
    ['От подчинённых', 'Средний балл от всех подчинённых (для руководителей)'],
    ['C-level', 'Корректировка или прямая оценка от топ-менеджмента'],
    ['Итоговый балл', 'Среднее арифметическое между оценкой менеджера и корректировками'],
    ['', ''],
    ['ГРУППЫ КРИТЕРИЕВ', ''],
    ['ОБЩИЕ', 'Критерии, применяемые ко всем сотрудникам'],
    ['ПРОЕКТНЫЕ', 'Критерии для участников проектной деятельности'],
    ['РУКОВОДСТВО', 'Критерии оценки управленческих навыков'],
    ['C-LEVEL', 'Стратегические критерии оценки'],
    ['', ''],
    ['МЕТОДОЛОГИЯ', ''],
    ['Диапазон оценок', 'От 1 до 10'],
    ['Расчет итога', 'Если есть корректировка C-level: Итог = (Менеджер + C-level) / 2']
  ];

  items.forEach((item, idx) => {
    if (idx === 0 || idx === 7 || idx === 13) {
      // Заголовки разделов
      ws[cellAddr(row, 0)] = styledCell(item[0], { ...STYLES.header, alignment: { horizontal: 'left', vertical: 'center' } });
      ws[cellAddr(row, 1)] = styledCell(item[1], { ...STYLES.header, alignment: { horizontal: 'left', vertical: 'center' } });
    } else if (item[0] === '') {
      // Пустая строка
      ws[cellAddr(row, 0)] = styledCell('', STYLES.cell);
      ws[cellAddr(row, 1)] = styledCell('', STYLES.cell);
    } else {
      ws[cellAddr(row, 0)] = styledCell(item[0], { ...STYLES.cell, font: { ...FONTS.cell, bold: true } });
      ws[cellAddr(row, 1)] = styledCell(item[1], { ...STYLES.cell, font: FONTS.legend });
    }
    row++;
  });

  ws['!ref'] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: row - 1, c: 1 } });
  ws['!cols'] = [{ wch: 25 }, { wch: 70 }];

  return ws;
};

export default exportMatrixToExcel;

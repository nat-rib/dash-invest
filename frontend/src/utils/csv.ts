/** Parser CSV mínimo no navegador, apenas para prévia do layout e mapeamento.
 * A validação autoritativa é sempre feita pelo backend (importador canônico). */

export function parseCsv(text: string, delimiter: string): string[][] {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (inQuotes) {
      if (char === '"') {
        if (text[index + 1] === '"') {
          field += '"';
          index += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
    } else if (char === '"') {
      inQuotes = true;
    } else if (char === delimiter) {
      row.push(field);
      field = "";
    } else if (char === "\r") {
      /* ignorado; LF é tratado como fim de linha */
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  // Última linha sem quebra final.
  const needsLastRow = field !== "" || row.length > 0;
  if (needsLastRow) {
    row.push(field);
    rows.push(row);
  }
  return rows.filter((line) => line.some((value) => value !== ""));
}

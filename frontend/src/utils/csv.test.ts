import { describe, expect, it } from "vitest";
import { parseCsv } from "./csv";

describe("parseCsv", () => {
  it("separa colunas e linhas", () => {
    expect(parseCsv("a;b\n1;2\n", ";")).toEqual([
      ["a", "b"],
      ["1", "2"],
    ]);
  });

  it("respeita aspas e aspas escapadas", () => {
    expect(parseCsv('nome;valor\n"Silva; Ana";"10""x"', ";")).toEqual([
      ["nome", "valor"],
      ["Silva; Ana", '10"x'],
    ]);
  });

  it("aceita CRLF e ignora linhas vazias", () => {
    expect(parseCsv("a,b\r\n1,2\r\n\r\n", ",")).toEqual([
      ["a", "b"],
      ["1", "2"],
    ]);
  });

  it("trata a última linha sem quebra final", () => {
    expect(parseCsv("a,b\n1,2", ",")).toEqual([
      ["a", "b"],
      ["1", "2"],
    ]);
  });
});

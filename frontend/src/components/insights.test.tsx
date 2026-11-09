import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResponsiveChart } from "./insights";

const points = [
  { label: "2026-11-01T12:00:00", value: 1000 },
  { label: "2026-11-02T12:00:00", value: 1500 },
  { label: "2026-11-03T12:00:00", value: 1200 },
];

function renderChart() {
  return render(
    <ResponsiveChart
      points={points}
      ariaLabel="patrimônio"
      formatValue={(value) => `R$ ${value}`}
      formatTick={(value) => `${value}`}
    />,
  );
}

describe("ResponsiveChart", () => {
  it("desenha linha, área e grade com escala", () => {
    const { container } = renderChart();

    expect(screen.getByRole("img", { name: "patrimônio" })).toBeTruthy();
    expect(container.querySelector("path.chart-line")?.getAttribute("d")).toMatch(/^M/);
    expect(container.querySelectorAll("path.chart-area")).toHaveLength(1);
    expect(container.querySelectorAll(".chart-grid-line").length).toBeGreaterThan(1);
  });

  it("rotula o eixo X com datas", () => {
    renderChart();
    expect(screen.getByText("01/11")).toBeTruthy();
    expect(screen.getByText("03/11")).toBeTruthy();
  });

  it("mostra tooltip com data e valor ao passar o ponteiro", () => {
    const { container } = renderChart();
    const overlay = container.querySelector("svg > rect");
    expect(overlay).not.toBeNull();

    fireEvent.pointerMove(overlay as SVGRectElement, { clientX: 0 });

    const tooltip = container.querySelector(".chart-tooltip");
    expect(tooltip?.textContent).toContain("R$ 1000");
  });

  it("posiciona o único ponto no centro da área de plotagem", () => {
    const { container } = render(
      <ResponsiveChart points={[{ label: "2026-11-01T12:00:00", value: 42 }]} ariaLabel="um ponto" />,
    );
    expect(container.querySelector("circle.chart-dot")?.getAttribute("cx")).toBe("390");
  });

  it("renderiza estado vazio sem eixo", () => {
    render(<ResponsiveChart points={[]} ariaLabel="vazio" />);
    expect(screen.queryByRole("img")).toBeNull();
  });
});

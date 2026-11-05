import { Children, cloneElement, isValidElement } from "react";
import type { ReactElement, ReactNode } from "react";

export function Card({ title, subtitle, children }: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="card">
      {title && <h2>{title}</h2>}
      {subtitle && <p className="muted">{subtitle}</p>}
      {children}
    </section>
  );
}

export function Button({ children, onClick, variant, disabled, type }: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type ?? "button"}
      className={`button ${variant ?? "ghost"}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function Field({ label, hint, children }: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function TextInput(props: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="text"
      value={props.value}
      placeholder={props.placeholder}
      onChange={(event) => props.onChange(event.target.value)}
    />
  );
}

export function SelectInput({ value, onChange, options }: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select value={value} onChange={(event) => onChange(event.target.value)}>
      {options.map((option) => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  );
}

export function Loading({ label }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <span className="spinner" aria-hidden="true" />
      {label ?? "Carregando…"}
    </div>
  );
}

export function ErrorBox({ message, children }: { message: string; children?: ReactNode }) {
  return (
    <div className="error-box" role="alert">
      <strong>Erro:</strong> {message}
      {children && <div className="error-children">{children}</div>}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="empty-state">
      <p>{title}</p>
      {hint && <p className="muted">{hint}</p>}
    </div>
  );
}

export function Badge({ children, tone }: { children: ReactNode; tone?: "good" | "warn" | "info" }) {
  return <span className={`badge ${tone ?? "info"}`}>{children}</span>;
}

export function Tabs({ tabs, active, onChange }: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={tab.id === active}
          className={`tab ${tab.id === active ? "active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function Table({ head, children, empty }: {
  head: string[];
  children: ReactNode;
  empty?: boolean;
}) {
  if (empty) return null;
  const stacked = head.length > 2;
  return (
    <div
      className={`table-wrap ${stacked ? "table-wrap-responsive" : ""}`.trim()}
      tabIndex={0}
      role="region"
      aria-label="Tabela de dados"
    >
      <table className={stacked ? "responsive-table" : undefined}>
        <thead>
          <tr>{head.map((label) => <th key={label}>{label}</th>)}</tr>
        </thead>
        <tbody>{stacked ? labelCells(children, head) : children}</tbody>
      </table>
    </div>
  );
}

// No mobile a tabela vira uma lista de cartões; cada célula recebe o cabeçalho
// como rótulo para continuar legível sem rolagem horizontal.
function labelCells(children: ReactNode, head: string[]): ReactNode {
  return Children.map(children, (row) => {
    if (!isValidElement(row)) return row;
    const rowProps = row.props as { children?: ReactNode };
    const cells = Children.map(rowProps.children, (cell, index) => {
      if (!isValidElement(cell)) return cell;
      return cloneElement(
        cell as ReactElement<{ "data-label"?: string }>,
        { "data-label": head[index] ?? "" },
      );
    });
    return cloneElement(row as ReactElement<{ children?: ReactNode }>, {}, cells);
  });
}

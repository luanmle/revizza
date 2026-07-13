import Page from "@/app/page";
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

test("home page renders a heading", () => {
  render(<Page />);
  expect(screen.getByRole("heading", { level: 1 })).toBeDefined();
});

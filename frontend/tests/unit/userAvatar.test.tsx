import { fireEvent, render } from "@testing-library/react";
import { expect, test } from "vitest";
import { UserAvatar } from "@/components/user-avatar";

test("reserva espaço e mantém fallback quando a imagem falha", () => {
  const { container, getByText } = render(
    <UserAvatar avatarUrl="https://example.com/avatar.png" name="Ana" />,
  );
  const image = container.querySelector("img")!;

  expect(image.width).toBe(32);
  expect(image.height).toBe(32);
  expect(image.getAttribute("loading")).toBe("lazy");
  expect(image.getAttribute("decoding")).toBe("async");

  fireEvent.error(image);

  expect(image.hidden).toBe(true);
  expect(getByText("A")).toBeDefined();
});

import tkinter as tk
from tkinter import ttk, messagebox


class ProductivityApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ажилтны бүтээмж")
        self.geometry("1100x700")
        self.protocol("WM_DELETE_WINDOW", self.on_close)  # X дарахад on_close ажиллана

        self.status = tk.StringVar(value="Систем бэлэн")
        ttk.Label(self, text="Ажилтны бүтээмжийг хянах систем", font=("Segoe UI", 16, "bold")).pack(pady=8)
        ttk.Label(self, textvariable=self.status).pack(side="bottom", pady=4)

        # 4 хэсэг: таб бүр нэг ttk.Frame
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10)
        self.frames = {}
        for name in ("Ажилтны бүртгэл", "Камер", "Компьютерийн идэвх", "Бүтээмж"):
            self.frames[name] = ttk.Frame(notebook, padding=10)
            notebook.add(self.frames[name], text=name)

        # register.py бэлэн болтол туршилтын өгөгдөл (7-р алхамд register.py-гаар солино)
        self.employees = [
            {"id": "emp-1", "name": "Хүслэн"},
            {"id": "emp-2", "name": "Бат"},
        ]
        self.next_id = 3

        self.build_employee(self.frames["Ажилтны бүртгэл"])

    def build_employee(self, frame):
        form = ttk.Frame(frame)
        form.pack(fill="x")
        ttk.Label(form, text="Нэр:").pack(side="left")
        self.name_entry = ttk.Entry(form, width=25)
        self.name_entry.pack(side="left", padx=5)
        self.add_btn = ttk.Button(form, text="Бүртгэх", command=self.add_employee_ui)
        self.add_btn.pack(side="left", padx=5)
        ttk.Button(form, text="Жагсаалт шинэчлэх", command=self.refresh_employees).pack(side="left")
        ttk.Button(form, text="Устгах", command=self.delete_selected_ui).pack(side="left", padx=5)

        self.tree = ttk.Treeview(frame, columns=("id", "name"), show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Нэр")
        self.tree.pack(fill="both", expand=True, pady=10)
        self.refresh_employees()

    def refresh_employees(self):
        for item in self.tree.get_children():  # хуучин мөрүүдийг арилгана
            self.tree.delete(item)
        for emp in self.employees:
            self.tree.insert("", "end", iid=emp["id"], values=(emp["id"], emp["name"]))
        self.status.set(f"Нийт ажилтан: {len(self.employees)}")

    def add_employee_ui(self):
        self.add_btn.config(state="disabled")  # давхар даралтаас сэргийлнэ
        self.after(500, lambda: self.add_btn.config(state="normal"))

        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Алдаа", "Нэрээ оруулна уу.")
            return

        self.employees.append({"id": f"emp-{self.next_id}", "name": name})
        self.next_id += 1
        self.refresh_employees()
        self.name_entry.delete(0, "end")
        self.status.set(f"{name} бүртгэгдлээ")

    def delete_selected_ui(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Алдаа", "Устгах ажилтнаа жагсаалтаас сонгоно уу.")
            return
        if messagebox.askyesno("Устгах", f"{len(selected)} ажилтныг устгах уу?"):
            self.employees = [e for e in self.employees if e["id"] not in selected]
            self.refresh_employees()

    def on_close(self):
        if messagebox.askokcancel("Гарах", "Программаас гарах уу?"):
            self.destroy()


if __name__ == "__main__":
    app = ProductivityApp()
    app.mainloop()

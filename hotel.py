import customtkinter as ctk
from tkinter import messagebox, simpledialog, ttk
import psycopg2

def check_login(username, password):
    user_passwords = {
        'st27699': 'Mst#27699',
        'st27700': 'Mst#27700',
        'st27701': 'Mst#27701',
    }
    return username in user_passwords and user_passwords[username] == password

def connect_to_db():
    connection = psycopg2.connect(
        host="localhost",
        database="Hotelguestregistration",
        user="postgres",
        password="1111"
    )
    return connection

class AddRecordDialog(simpledialog.Dialog):
    def __init__(self, parent, table_name):
        self.table_name = table_name
        super().__init__(parent, title=f"Добавить запись в {table_name}")

    def body(self, parent):
        self.entries = {}
        for column in table_columns[self.table_name]:
            label = ttk.Label(parent, text=column)
            label.pack(side='left')
            entry = ttk.Entry(parent)
            entry.pack(side='left')
            self.entries[column] = entry
        return parent

    def validate(self):
        self.result = [entry.get() for entry in self.entries.values()]
        return True

class SortDialog(simpledialog.Dialog):
    def __init__(self, parent, columns):
        self.columns = columns
        self.result = None
        super().__init__(parent, title="Сортировать по:")

    def body(self, parent):
        self.combobox = ttk.Combobox(parent, values=self.columns)
        self.combobox.pack()
        return self.combobox

    def apply(self):
        self.result = self.combobox.get()

    def show(self):
        self.wm_deiconify()
        self.wait_window()
        return self.result

def get_data_from_table(table_name):
    data = []
    try:
        with connect_to_db() as connection:
            with connection.cursor() as cursor:
                query = ""
                if table_name == 'room':
                    query = """
                    SELECT room.Room, hotel.Name as Hotel, roomtype.Name as Type, room.Status
                    FROM room
                    INNER JOIN hotel ON room.HotelID = hotel.HotelID
                    INNER JOIN roomtype ON room.TypeID = roomtype.TypeID
                    """
                elif table_name == 'booking':
                    query = """
                    SELECT hotel.Name as Hotel, booking.GuestID, booking.Room, booking.CheckinDate, booking.CheckOutDate, booking.TotalPrice
                    FROM booking
                    INNER JOIN hotel ON booking.HotelID = hotel.HotelID
                    """
                elif table_name == 'guest':
                    query = "SELECT FirstName, LastName, DateOfBirth, Address, Phone, Email FROM guest"
                else:
                    query = "SELECT * FROM %s"
                    cursor.execute(query, (table_name,))
                if query:
                    cursor.execute(query)
                data = cursor.fetchall()
    except psycopg2.DatabaseError as e:
        print(f"Произошла ошибка базы данных: {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
    return data

def populate_table(tree, table_name):
    data = get_data_from_table(table_name)
    for datum in data:
        tree.insert('', 'end', values=datum)

def delete_record(tree, table_name):
    selected_items = tree.selection()
    if not selected_items:
        print('Выберите запись для удаления')
        return
    selected_item = selected_items[0]
    values = tree.item(selected_item)['values']
    hotel_name = values[0]
    guest_id = values[1]
    room = values[2]
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("SELECT HotelID FROM hotel WHERE Name = %s", (hotel_name,))
        hotel_id = cursor.fetchone()[0]
        cursor.execute(
            "DELETE FROM {} WHERE HotelID = %s AND GuestID = %s AND Room = %s".format(table_name),
            (hotel_id, guest_id, room)
        )
        cursor.execute(
            "UPDATE room SET Status = 'Available' WHERE Room = %s",
            (room,)
        )
        connection.commit()
        tree.delete(selected_item)
    except psycopg2.Error as e:
        print(f"Произошла ошибка: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()

def add_record(tree, table_name):
    dialog = AddRecordDialog(root, table_name)
    if dialog.result is not None:
        values = dialog.result
        connection = connect_to_db()
        cursor = connection.cursor()
        placeholders = ', '.join(['%s'] * len(values))
        cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
        if table_name == "booking":
            hotel_id = values[0]
            room_id = values[2]
            cursor.execute("UPDATE room SET Status = 'Booked' WHERE Room = %s AND HotelID = %s", (room_id, hotel_id))
        connection.commit()
        connection.close()
        tree.insert('', 'end', values=values)

def sort_record(tree, table_name):
    columns = table_columns[table_name]
    dialog = SortDialog(root, columns)
    if dialog.result is not None:
        column = dialog.result
        data = get_data_from_table(table_name)
        data.sort(key=lambda x: x[table_columns[table_name].index(column)])
        for i in tree.get_children():
            tree.delete(i)
        for datum in data:
            tree.insert('', 'end', values=datum)

def login():
    username = username_entry.get()
    password = password_entry.get()
    if username and password:
        if check_login(username, password):
            messagebox.showinfo("Успешный вход", "Добро пожаловать, Администратор!")
            login_window.destroy()
            open_admin_interface()
        else:
            messagebox.showinfo("Успешный вход", "Добро пожаловать, Пользователь!")
            login_window.destroy()
            open_user_interface()
    else:
        messagebox.showerror("Ошибка", "Пожалуйста, введите имя пользователя и пароль")

def open_admin_interface():
    root = ctk.CTk()
    ctk.set_appearance_mode("dark")
    root.title("Administrator Dashboard")
    root.after(0, lambda:root.state('zoomed')) 
    notebook = ttk.Notebook(root)
    table_names1 = ["guest", "room", "booking"]
    trees = []
    for table_name in table_names1:
        frame, tree = create_table_frame(notebook, table_name)
        trees.append(tree)
        notebook.add(frame, text=table_name)
    notebook.grid(row=0, column=0, sticky='nw')
    def refresh_data():
        for index, table_name in enumerate(table_names1):
            tree = trees[index]
            for i in tree.get_children():
                tree.delete(i)
            populate_table(tree, table_name)
        root.after(5000, refresh_data)
    refresh_data()
    def finish():
        root.destroy()
        print('Закрытие приложения')
    root.protocol('WM_DELETE_WINDOW', finish)
    root.mainloop()

def open_user_interface():
    root = ctk.CTk()
    ctk.set_appearance_mode("dark")
    root.title("Hotel ElPresento")
    root.after(0, lambda:root.state('zoomed')) 
    notebook = ttk.Notebook(root)
    table_names = ["room"]
    for table_name in table_names:
        frame, tree = create_table_frame(notebook, table_name)
        notebook.add(frame, text=table_name)
    notebook.grid(row=0, column=0, sticky='nw')
    def finish():
        root.destroy()
        print('Закрытие приложения')
    root.protocol('WM_DELETE_WINDOW', finish)
    root.mainloop()

# Создание и настройка главного окна приложения
root = ctk.CTk()
ctk.set_appearance_mode("dark")  # Установка темной темы для всего приложения
root.title("ElPresento - Главное окно")

# Создаем Notebook (вкладки)
notebook = ttk.Notebook(root)

# Создаем вкладки
tab1 = ctk.CTkFrame(notebook)
tab2 = ctk.CTkFrame(notebook)
tab3 = ctk.CTkFrame(notebook)

# Добавляем вкладки в Notebook
notebook.add(tab1, text='Брони')
notebook.add(tab2, text='Гости')
notebook.add(tab3, text='Комнаты')

# Определение столбцов для таблицы
table_columns = {
    "hotel": ["HotelID", "Name", "Address", "Phone", "Email"],
    "room": ["Room", "Hotel", "Type", "Status"],
    "roomtype": ["TypeID", "Name", "Description", "PricePerNight", "Capacity"],
    "booking": ["Hotel", "GuestID", "Room", "CheckinDate", "CheckOutDate", "TotalPrice"],
    "guest": ["FirstName", "LastName", "DateOfBirth", "Address", "Phone", "Email"],
    "stuff": ["StuffID", "HotelID", "FirstName", "LastName", "Position", "Salary", "DateOfBirth", "Phone", "Email", "HireDate"]
}

tree = ctk.CTkTreeview(tab1, columns=table_columns["booking"], show='headings')
for column in table_columns["booking"]:
    tree.heading(column, text=column)
tree.pack(expand=True, fill='both')

delete_button = ctk.CTkButton(tab1, text="Удалить", command=delete_record)
add_button = ctk.CTkButton(tab1, text="Добавить", command=add_record)
sort_button = ctk.CTkButton(tab1, text="Сортировать", command=sort_record)

delete_button.pack(side='left')
add_button.pack(side='left')
sort_button.pack(side='left')

notebook.pack(expand=True, fill='both')
root.mainloop()

# Создание и настройка окна входа
login_window = ctk.CTk()
ctk.set_appearance_mode("dark")  # Установка темной темы для окна входа
login_window.title("ElPresento - Вход")

# Элементы интерфейса для окна входа
username_label = ctk.CTkLabel(login_window, text="Имя пользователя")
username_entry = ctk.CTkEntry(login_window)
password_label = ctk.CTkLabel(login_window, text="Пароль")
password_entry = ctk.CTkEntry(login_window, show="*")
login_button = ctk.CTkButton(login_window, text="Войти", command=login)

# Расположение элементов на окне входа
username_label.grid(row=0, column=0, padx=10, pady=10)
username_entry.grid(row=0, column=1, padx=10, pady=10)
password_label.grid(row=1, column=0, padx=10, pady=10)
password_entry.grid(row=1, column=1, padx=10, pady=10)
login_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

login_window.mainloop()
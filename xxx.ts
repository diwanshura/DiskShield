export interface Employee {
  readonly id: number;
  name: string;
  position: string;
  department: string;
  salary: number;
  isActive: boolean;
}

export interface NewEmployee {
  name: string;
  position: string;
  department: string;
  salary: number;
  isActive?: boolean;
}

export type EmployeeUpdate = Partial<Omit<Employee, 'id'>>;

const assertNonEmptyString = (value: string, field: string): void => {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`${field} must be a non-empty string.`);
  }
};

const assertSalary = (salary: number): void => {
  if (!Number.isFinite(salary) || salary < 0) {
    throw new Error('Salary must be a non-negative number.');
  }
};

const validateNewEmployee = (employee: NewEmployee): void => {
  assertNonEmptyString(employee.name, 'name');
  assertNonEmptyString(employee.position, 'position');
  assertNonEmptyString(employee.department, 'department');
  assertSalary(employee.salary);
};

const validateEmployeeUpdate = (changes: EmployeeUpdate): void => {
  if (changes.name !== undefined) {
    assertNonEmptyString(changes.name, 'name');
  }

  if (changes.position !== undefined) {
    assertNonEmptyString(changes.position, 'position');
  }

  if (changes.department !== undefined) {
    assertNonEmptyString(changes.department, 'department');
  }

  if (changes.salary !== undefined) {
    assertSalary(changes.salary);
  }
};

export class EmployeeRecordSystem {
  private readonly employees = new Map<number, Employee>();
  private nextId = 1;

  addEmployee(employee: NewEmployee): Employee {
    validateNewEmployee(employee);

    const record: Employee = {
      id: this.nextId++,
      name: employee.name.trim(),
      position: employee.position.trim(),
      department: employee.department.trim(),
      salary: employee.salary,
      isActive: employee.isActive ?? true,
    };

    this.employees.set(record.id, record);
    return { ...record };
  }

  updateEmployee(id: number, changes: EmployeeUpdate): Employee | null {
    const current = this.employees.get(id);
    if (!current) {
      return null;
    }

    validateEmployeeUpdate(changes);

    const updated: Employee = {
      ...current,
      ...changes,
      name: changes.name?.trim() ?? current.name,
      position: changes.position?.trim() ?? current.position,
      department: changes.department?.trim() ?? current.department,
    };

    this.employees.set(id, updated);
    return { ...updated };
  }

  deleteEmployee(id: number): boolean {
    return this.employees.delete(id);
  }

  displayEmployees(): Employee[] {
    return Array.from(this.employees.values(), (employee) => ({ ...employee }));
  }
}

const registry = new EmployeeRecordSystem();

registry.addEmployee({
  name: 'Alice Johnson',
  position: 'Software Engineer',
  department: 'Engineering',
  salary: 90000,
});

registry.addEmployee({
  name: 'Bob Smith',
  position: 'HR Manager',
  department: 'Human Resources',
  salary: 65000,
  isActive: false,
});

registry.updateEmployee(1, { salary: 95000, position: 'Senior Software Engineer' });
registry.deleteEmployee(2);

console.log('Employee records:', registry.displayEmployees());

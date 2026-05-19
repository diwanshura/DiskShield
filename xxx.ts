interface Employee {
  id: number;
  name: string;
  age: number;
  role: string;
  salary: number;
  isActive: boolean;
}

type EmployeeInput = Omit<Employee, 'id'>;
type EmployeeUpdate = Partial<EmployeeInput>;

class EmployeeRecordSystem {
  private readonly employees = new Map<number, Employee>();
  private nextId = 1;

  addEmployee(input: EmployeeInput): Employee {
    this.validateEmployeeInput(input);

    const employee: Employee = {
      id: this.nextId++,
      ...input,
    };

    this.employees.set(employee.id, employee);
    return employee;
  }

  updateEmployee(id: number, updates: EmployeeUpdate): Employee {
    const existing = this.employees.get(id);
    if (!existing) {
      throw new Error(`Employee with id ${id} does not exist.`);
    }

    this.validateEmployeeUpdate(updates);

    const updated: Employee = {
      ...existing,
      ...updates,
    };

    this.employees.set(id, updated);
    return updated;
  }

  deleteEmployee(id: number): boolean {
    return this.employees.delete(id);
  }

  displayEmployees(): readonly Employee[] {
    return Array.from(this.employees.values()).sort((a, b) => a.id - b.id);
  }

  private validateEmployeeInput(input: EmployeeInput): void {
    if (!this.isNonEmptyString(input.name)) {
      throw new Error('Name must be a non-empty string.');
    }

    if (!Number.isInteger(input.age) || input.age <= 0) {
      throw new Error('Age must be a positive integer.');
    }

    if (!this.isNonEmptyString(input.role)) {
      throw new Error('Role must be a non-empty string.');
    }

    if (typeof input.salary !== 'number' || !Number.isFinite(input.salary) || input.salary < 0) {
      throw new Error('Salary must be a non-negative finite number.');
    }

    if (typeof input.isActive !== 'boolean') {
      throw new Error('isActive must be a boolean.');
    }
  }

  private validateEmployeeUpdate(updates: EmployeeUpdate): void {
    if (Object.keys(updates).length === 0) {
      throw new Error('At least one field is required to update employee.');
    }

    if (updates.name !== undefined && !this.isNonEmptyString(updates.name)) {
      throw new Error('Name must be a non-empty string.');
    }

    if (updates.age !== undefined && (!Number.isInteger(updates.age) || updates.age <= 0)) {
      throw new Error('Age must be a positive integer.');
    }

    if (updates.role !== undefined && !this.isNonEmptyString(updates.role)) {
      throw new Error('Role must be a non-empty string.');
    }

    if (
      updates.salary !== undefined &&
      (typeof updates.salary !== 'number' || !Number.isFinite(updates.salary) || updates.salary < 0)
    ) {
      throw new Error('Salary must be a non-negative finite number.');
    }

    if (updates.isActive !== undefined && typeof updates.isActive !== 'boolean') {
      throw new Error('isActive must be a boolean.');
    }
  }

  private isNonEmptyString(value: unknown): boolean {
    return typeof value === 'string' && value.trim().length > 0;
  }
}

export type { Employee, EmployeeInput, EmployeeUpdate };
export { EmployeeRecordSystem };

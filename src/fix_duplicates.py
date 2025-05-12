# Script to fix duplicated function definitions in page4_shopping.py
with open('src/page4_shopping.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all the lines where the function is defined
function_lines = []
for i, line in enumerate(lines):
    if 'def show_synchronized_toast(self, message):' in line:
        function_lines.append(i)

print(f"Found {len(function_lines)} occurrences of the function at lines: {function_lines}")

if len(function_lines) <= 1:
    print("No duplicates found, nothing to fix.")
    exit(0)

# Find the end of the first function (next function definition after the first instance)
first_function_start = function_lines[0]
next_function_start = None

for i in range(first_function_start + 1, len(lines)):
    if '    def ' in lines[i]:
        next_function_start = i
        break

if next_function_start is None:
    print("Could not find the end of the first function.")
    exit(1)

print(f"First function: lines {first_function_start}-{next_function_start-1}")

# Find the main section
main_line = None
for i, line in enumerate(lines):
    if "if __name__ == '__main__':" in line:
        main_line = i
        break

if main_line is None:
    print("Could not find the main section.")
    exit(1)

print(f"Main section starts at line {main_line}")

# Create the fixed file
with open('src/page4_fixed.py', 'w', encoding='utf-8') as f:
    # Write everything until the first function
    f.writelines(lines[:first_function_start])
    
    # Write the first function implementation
    for i in range(first_function_start, next_function_start):
        f.write(lines[i])
    
    # Skip all duplicates and write next function after the last duplicate
    if function_lines[-1] + 1 < main_line:
        next_real_function = None
        for i in range(function_lines[-1] + 1, main_line):
            if '    def ' in lines[i]:
                next_real_function = i
                break
        
        if next_real_function:
            print(f"Next real function after duplicates: line {next_real_function}")
            f.writelines(lines[next_real_function:main_line])
    
    # Write main section to the end
    f.writelines(lines[main_line:])

print("Fixed file created as src/page4_fixed.py") 
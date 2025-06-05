#!/usr/bin/env psh

# Basic select menu
echo "=== Basic Fruit Selection ==="
select fruit in apple banana cherry quit; do
    case $fruit in
        apple|banana|cherry)
            echo "You selected: $fruit"
            ;;
        quit)
            echo "Goodbye!"
            break
            ;;
        *)
            echo "Invalid option: $REPLY"
            ;;
    esac
done

# Custom PS3 prompt
echo -e "\n=== File Operations Menu ==="
PS3="Enter your choice (1-4): "
select operation in "List files" "Show date" "Print working directory" "Exit"; do
    case $operation in
        "List files")
            ls -la
            ;;
        "Show date")
            date
            ;;
        "Print working directory")
            pwd
            ;;
        "Exit")
            break
            ;;
        *)
            echo "Please select a valid option (1-4)"
            ;;
    esac
done

# Dynamic menu from command output
echo -e "\n=== Select a Shell Script ==="
select script in *.sh "None"; do
    if [[ "$script" == "None" ]]; then
        echo "No script selected"
        break
    elif [[ -n "$script" ]]; then
        echo "You selected: $script"
        echo "First line: $(head -n1 "$script")"
        break
    else
        echo "Invalid selection: $REPLY"
    fi
done

# Nested select example
echo -e "\n=== Restaurant Order System ==="
select category in "Appetizers" "Main Courses" "Desserts" "Done"; do
    case $category in
        "Appetizers")
            echo "Choose an appetizer:"
            select item in "Salad" "Soup" "Bread" "Back"; do
                if [[ "$item" == "Back" ]]; then
                    break
                elif [[ -n "$item" ]]; then
                    echo "Added $item to your order"
                fi
            done
            ;;
        "Main Courses")
            echo "Choose a main course:"
            select item in "Steak" "Fish" "Pasta" "Back"; do
                if [[ "$item" == "Back" ]]; then
                    break
                elif [[ -n "$item" ]]; then
                    echo "Added $item to your order"
                fi
            done
            ;;
        "Desserts")
            echo "Choose a dessert:"
            select item in "Ice Cream" "Cake" "Fruit" "Back"; do
                if [[ "$item" == "Back" ]]; then
                    break
                elif [[ -n "$item" ]]; then
                    echo "Added $item to your order"
                fi
            done
            ;;
        "Done")
            echo "Thank you for your order!"
            break
            ;;
        *)
            echo "Please select a valid category"
            ;;
    esac
done

# Configuration example
echo -e "\n=== System Configuration ==="
PS3="Configure option> "
select option in "Enable debugging" "Set log level" "View settings" "Save & Exit"; do
    case $option in
        "Enable debugging")
            echo "Debug mode enabled"
            DEBUG=1
            ;;
        "Set log level")
            select level in "ERROR" "WARN" "INFO" "DEBUG" "Back"; do
                if [[ "$level" == "Back" ]]; then
                    break
                elif [[ -n "$level" ]]; then
                    echo "Log level set to: $level"
                    LOG_LEVEL=$level
                    break
                fi
            done
            ;;
        "View settings")
            echo "Current settings:"
            echo "  Debug: ${DEBUG:-0}"
            echo "  Log level: ${LOG_LEVEL:-INFO}"
            ;;
        "Save & Exit")
            echo "Settings saved!"
            break
            ;;
        *)
            echo "Invalid option: $REPLY"
            ;;
    esac
done
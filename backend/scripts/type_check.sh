#!/bin/bash
# Type checking script for backend

echo "Running mypy type check..."
cd backend
python -m mypy app/ --config-file mypy.ini
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ Type check passed!"
else
    echo "❌ Type check failed with exit code $exit_code"
fi

exit $exit_code

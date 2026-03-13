#!/bin/bash
# Type checking script for frontend

echo "Running TypeScript type check..."
cd frontend
npx vue-tsc --noEmit
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ Type check passed!"
else
    echo "❌ Type check failed with exit code $exit_code"
fi

exit $exit_code

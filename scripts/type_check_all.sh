#!/bin/bash
# Combined type checking script

echo "=========================================="
echo "Running Type Checks for Interview Service"
echo "=========================================="
echo ""

# Backend type check
echo "🔍 Checking Backend Types..."
cd backend
python -m mypy app/ --config-file mypy.ini
backend_status=$?
cd ..

if [ $backend_status -eq 0 ]; then
    echo "✅ Backend type check passed!"
else
    echo "❌ Backend type check failed!"
fi

echo ""
echo "🔍 Checking Frontend Types..."
cd frontend
npx vue-tsc --noEmit
frontend_status=$?
cd ..

if [ $frontend_status -eq 0 ]; then
    echo "✅ Frontend type check passed!"
else
    echo "❌ Frontend type check failed!"
fi

echo ""
echo "=========================================="
if [ $backend_status -eq 0 ] && [ $frontend_status -eq 0 ]; then
    echo "✅ All type checks passed!"
    exit 0
else
    echo "❌ Some type checks failed!"
    exit 1
fi

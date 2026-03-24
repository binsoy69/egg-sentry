@echo off
npm.cmd create vite@latest frontend -- --template react
cd frontend
call npm.cmd install
call npm.cmd install -D tailwindcss postcss autoprefixer
call npx.cmd tailwindcss init -p
call npm.cmd install react-router-dom recharts axios lucide-react date-fns clsx tailwind-merge
echo Setup Complete

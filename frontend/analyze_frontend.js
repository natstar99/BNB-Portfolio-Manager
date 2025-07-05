#!/usr/bin/env node
/**
 * Frontend Code Usage Analysis
 * Analyzes React/TypeScript code for unused components, imports, and dependencies
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function runCommand(command, description) {
    console.log(`\n🔍 ${description}`);
    console.log(`Running: ${command}`);
    console.log('-'.repeat(50));
    
    try {
        const output = execSync(command, { encoding: 'utf8', stdio: 'pipe' });
        console.log(output);
        return output;
    } catch (error) {
        console.log(`❌ Error: ${error.message}`);
        if (error.stdout) console.log(error.stdout);
        if (error.stderr) console.log(error.stderr);
        return null;
    }
}

function analyzeComponents() {
    console.log('\n📦 COMPONENT USAGE ANALYSIS');
    console.log('='.repeat(50));
    
    // Find all component files
    const srcDir = path.join(process.cwd(), 'src');
    const componentFiles = [];
    
    function findComponents(dir) {
        const files = fs.readdirSync(dir);
        for (const file of files) {
            const filePath = path.join(dir, file);
            const stat = fs.statSync(filePath);
            
            if (stat.isDirectory()) {
                findComponents(filePath);
            } else if (file.match(/\.(tsx|ts|jsx|js)$/) && !file.includes('.test.') && !file.includes('.spec.')) {
                componentFiles.push(filePath);
            }
        }
    }
    
    if (fs.existsSync(srcDir)) {
        findComponents(srcDir);
        
        console.log(`📄 Found ${componentFiles.length} component files`);
        
        // Analyze imports and exports
        const importUsage = new Map();
        const exportUsage = new Map();
        
        for (const file of componentFiles) {
            const content = fs.readFileSync(file, 'utf8');
            const relativePath = path.relative(srcDir, file);
            
            // Find imports
            const importMatches = content.match(/import\s+{([^}]+)}\s+from\s+['"](\.\/|\.\.\/)[^'"]+['"]/g);
            if (importMatches) {
                for (const match of importMatches) {
                    const imports = match.match(/{([^}]+)}/)[1]
                        .split(',')
                        .map(s => s.trim())
                        .filter(s => s.length > 0);
                    
                    for (const imp of imports) {
                        if (!importUsage.has(imp)) {
                            importUsage.set(imp, []);
                        }
                        importUsage.get(imp).push(relativePath);
                    }
                }
            }
            
            // Find exports
            const exportMatches = content.match(/export\s+(const|function|class|interface|type)\s+(\w+)/g);
            if (exportMatches) {
                for (const match of exportMatches) {
                    const exportName = match.split(/\s+/).pop();
                    if (!exportUsage.has(exportName)) {
                        exportUsage.set(exportName, []);
                    }
                    exportUsage.get(exportName).push(relativePath);
                }
            }
        }
        
        // Report potentially unused exports
        console.log('\n❓ POTENTIALLY UNUSED EXPORTS:');
        for (const [exportName, files] of exportUsage.entries()) {
            if (!importUsage.has(exportName)) {
                console.log(`   ${exportName} (exported in: ${files.join(', ')})`);
            }
        }
        
        // Report import statistics
        console.log('\n📊 IMPORT STATISTICS:');
        console.log(`   Total unique imports: ${importUsage.size}`);
        console.log(`   Total unique exports: ${exportUsage.size}`);
    }
}

function main() {
    console.log('⚛️  FRONTEND CODE USAGE ANALYSIS');
    console.log('='.repeat(60));
    
    // Check if we're in a React project
    if (!fs.existsSync('package.json')) {
        console.log('❌ Error: No package.json found. Run this from the frontend directory.');
        process.exit(1);
    }
    
    try {
        // 1. Install analysis dependencies if needed
        console.log('\n🔧 INSTALLING ANALYSIS TOOLS');
        runCommand('npm install --save-dev depcheck ts-unused-exports', 'Installing analysis dependencies');
        
        // 2. Check for unused dependencies
        console.log('\n📦 UNUSED DEPENDENCIES');
        runCommand('npx depcheck', 'Checking for unused npm dependencies');
        
        // 3. Check for unused TypeScript exports
        console.log('\n📤 UNUSED TYPESCRIPT EXPORTS');
        if (fs.existsSync('tsconfig.json')) {
            runCommand('npx ts-unused-exports tsconfig.json', 'Finding unused TypeScript exports');
        } else {
            console.log('ℹ️  No tsconfig.json found, skipping TypeScript analysis');
        }
        
        // 4. Analyze component usage
        analyzeComponents();
        
        // 5. Generate test coverage if possible
        console.log('\n🧪 TEST COVERAGE ANALYSIS');
        if (fs.existsSync('src')) {
            runCommand('npm test -- --coverage --watchAll=false --passWithNoTests', 'Generating test coverage report');
        }
        
        // 6. Bundle size analysis
        console.log('\n📊 BUNDLE SIZE ANALYSIS');
        runCommand('npm run build', 'Building for production to analyze bundle size');
        
        console.log('\n✅ FRONTEND ANALYSIS COMPLETE!');
        console.log('📄 Check the coverage/ directory for detailed reports');
        console.log('🔗 Open coverage/lcov-report/index.html for interactive coverage report');
        
    } catch (error) {
        console.log(`\n❌ Analysis failed: ${error.message}`);
    }
}

if (require.main === module) {
    main();
}
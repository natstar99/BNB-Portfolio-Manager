# BNB Portfolio Manager - Application Architecture & Requirements

**PURPOSE**: This is a living, centralised document that captures the vision, intent, and evolving implementation of the BNB Portfolio Manager. This document is designed for development team reference and contains the complete context including requirements, philosophy, technical decisions, lessons learned, and critical implementation details that must not be forgotten.

**INSTRUCTIONS FOR FUTURE REFERENCE**: Always read relevant sections of this document before making changes to any component. This document contains the complete context that otherwise gets lost, including user requirements, design decisions, and debugging lessons. Update this document as the application evolves, but preserve historical context where relevant.

---

## 1. APPLICATION OVERVIEW

### Core Philosophy
- **Portfolio-First Navigation Paradigm**: The application is built around the principle that users always work within a specific portfolio context. No transaction or stock operations exist in isolation.
- **Kimball Star Schema Architecture**: All data is structured using dimensional modeling principles for optimal analytics performance.
- **User-Controlled Data Quality**: Users maintain complete control over data verification and market assignments, with the system providing intelligent assistance rather than making automatic decisions.

### Technology Stack
- **Frontend**: React 18 + TypeScript, CSS Variables for theming
- **Backend**: Flask + SQLAlchemy ORM, Python 3.12
- **Database**: SQLite with Kimball Star Schema design
- **External APIs**: Yahoo Finance for market data and stock verification
- **Architecture**: REST API with staged ETL processing

---

## 2. TRANSACTION IMPORT WORKFLOW - DETAILED REQUIREMENTS

### The Revolutionary Approach  
**CRITICAL DESIGN PHILOSOPHY**: The user emphasized starting fresh rather than being constrained by existing code:
1. Understand complete requirements first
2. Design optimal solution architecture  
3. Assess if existing code meets requirements
4. Remove and restart components that don't align
5. **NO PREMATURE ABSTRACTION** - build exactly what's needed

### Complete Workflow Steps (EXACT USER REQUIREMENTS)

#### Step 1: File Upload & Column Mapping + Date Format Selection
- **Status**: ✅ IMPLEMENTED AND WORKING
- **Purpose**: Establish data structure and format configuration
- **Process**:
  - User uploads CSV/Excel file
  - System detects column structure and suggests mappings  
  - User confirms/adjusts column mappings to required fields
  - **CRITICAL**: User selects date format (moved from validation step)
  - All configuration completed in single step
- **Required Fields**: Date, Instrument Code, Transaction Type, Quantity, Price, Total Value (optional)
- **Files**: `ColumnMapping.tsx`, `FileUpload.tsx`
- **Database Impact**: None (file analysis only)

#### Step 2: Raw Data Confirmation (CRITICAL TERMINOLOGY)
- **Status**: 🔄 NEEDS FRONTEND IMPLEMENTATION
- **CRITICAL TERMINOLOGY**: Must use "Confirm Raw Data" - NOT "verify"
- **"Verify" is reserved EXCLUSIVELY for Yahoo Finance API calls**
- **ZERO external API calls during this step**

**Detailed Process**:
1. **Data Quality Validation**: 
   - Validate all dates parse correctly with selected format
   - Ensure all required fields present (no missing gaps)
   - Check data type conversions (quantities, prices)
   - Validate transaction types against allowed values

2. **Duplicate Detection**:
   - Compare against existing portfolio transactions
   - Exact match on: date, instrument_code, quantity, price, transaction_type
   - Count duplicates (these will be skipped in import)

3. **Summary Statistics**:
   - Total transactions in file
   - New transactions (not duplicates)
   - Duplicate transactions (will be skipped)
   - New stock tickers found (not in portfolio)
   - Existing stock tickers (already in portfolio)

4. **User Confirmation Interface**:
   - **Present as popup confirmation dialog**
   - Show all summary statistics clearly
   - Two options: "Confirm and Proceed" or "Go Back to Fix Data"
   - **NO PROCEEDING** until user explicitly confirms

**Database Flow**:
```
File Data → STG_RAW_TRANSACTIONS (with import_batch_id)
├── processed_flag = FALSE  
├── validation_errors = NULL (if valid) or error details
└── Data staged but NOT processed into fact tables yet
```

**API**: `POST /api/import/validate` → Enhanced validation with summary
**Files**: `DataPreview.tsx` (major update needed), `TransactionImportService.confirm_raw_data()`

#### Step 3: Stock Market Assignment & Lightweight Verification
- **Status**: 🔄 NEEDS COMPLETE IMPLEMENTATION  
- **Purpose**: Assign market codes to construct proper Yahoo Finance symbols
- **CRITICAL**: Only triggers for NEW stocks not already in portfolio

**The Market Code Problem**:
- Raw data contains: "AFI" (just the ticker)
- Yahoo Finance requires: "AFI.AX" (ticker + market suffix)
- User must select market to construct proper Yahoo symbol

**Table Interface Requirements**:

| Column | Purpose | Behavior |
|--------|---------|----------|
| **Ticker** | Raw instrument code from data | Display only (e.g., "AFI") |
| **Market** | User-selectable dropdown | 87 Yahoo market codes available |
| **Yahoo Symbol** | Auto-constructed symbol | Updates immediately when market selected (e.g., "AFI.AX") |
| **Stock Name** | Retrieved from Yahoo | Blank initially, populated after verification |
| **Currency** | Retrieved from Yahoo | Blank initially, populated after verification |
| **DRP** | Dividend Reinvestment Plan flag | User can enable for this portfolio |
| **Status** | Verification status | Delisted/Verified/Pending/Failed |
| **Actions** | Action menu dropdown | Manual verify, corporate actions, mark delisted |

**Status Field Values**:
- **Pending**: Not yet verified OR market assignment changed and needs re-verification
- **Verified**: Successfully retrieved data from Yahoo Finance  
- **Failed**: Attempted verification but Yahoo Finance returned error
- **Delisted**: User-marked as delisted (skip verification)

**Verification Process (Lightweight)**:
- **PURPOSE**: Prove Yahoo symbol is valid endpoint
- **RETRIEVES**: Stock name and currency ONLY
- **NO HISTORICAL DATA** retrieval at this stage
- **API Call**: `MarketDataService.verify_stock_lightweight(yahoo_symbol)`

**User Workflow**:
1. Table shows all new stocks requiring market assignment
2. User selects market from dropdown for each stock
3. Yahoo symbol auto-updates (ticker + market_suffix)
4. User can trigger verification for individual stocks or batch
5. Verification populates stock name/currency if successful
6. User can mark stocks as delisted to skip verification
7. User can set DRP flags for portfolio-specific settings

**Database Flow**:
```
New Stocks → DIM_STOCK (created with pending status)
├── instrument_code: "AFI"  
├── yahoo_symbol: "AFI.AX" (after market assignment)
├── market_key: Foreign key to DIM_YAHOO_MARKET_CODES
├── verification_status: 'pending'/'verified'/'failed'/'delisted'
├── name: NULL initially, populated after verification
└── currency: NULL initially, populated after verification

Portfolio Settings → PORTFOLIO_STOCK_CONFIG  
├── drp_enabled: User-set DRP flag
└── notes: User notes if any
```

**APIs**:
- `GET /api/import/markets` → Returns all 87 market codes
- `POST /api/import/assign-markets` → Assigns markets and verifies stocks
- `POST /api/stocks/verify-lightweight` → Individual stock verification

**Files**: `StockMarketAssignment.tsx` (needs creation), `MarketDataService.verify_stock_lightweight()`

#### Step 4: Final Transaction Import  
- **Status**: 🔄 NEEDS IMPLEMENTATION
- **Purpose**: Process validated data into database fact tables
- **Prerequisite**: All stocks must be assigned markets (verified or marked delisted)

**Database Transaction Flow**:
```
STG_RAW_TRANSACTIONS (processed_flag=FALSE) 
↓
FACT_TRANSACTIONS (with all dimension keys resolved)
↓  
PORTFOLIO_POSITIONS (updated with new transactions)
↓
STG_RAW_TRANSACTIONS (processed_flag=TRUE)
```

**Skip Logic**:
- **Duplicate transactions**: Identified in Step 2, marked for skipping
- **Unverified stocks**: If user chooses to skip unverified stocks
- **Delisted stocks**: User-marked delisted stocks can be imported or skipped per user choice

**Position Calculations**:
- Update `PORTFOLIO_POSITIONS` with new transaction impacts
- Recalculate average cost, current quantity, unrealized P&L
- Handle different transaction types (BUY/SELL/DIVIDEND/SPLIT)

**Error Handling**:
- **Atomic operation**: All transactions succeed or all rollback
- **Detailed reporting**: Report exactly which transactions succeeded/failed
- **Next import behavior**: Failed transactions remain in staging for retry

**API**: `POST /api/import/transactions` → Complete import processing
**Files**: `ImportSummary.tsx`, `TransactionImportService.process_file_import()`

### Critical Database Flow Analysis

#### Kimball Star Schema ETL Process (DETAILED)

**Stage 1: Raw Data Staging**
```sql
STG_RAW_TRANSACTIONS
├── id (PK, auto-increment)
├── import_batch_id (groups single import session)
├── portfolio_id (FK to target portfolio)  
├── raw_date (TEXT - unparsed date from file)
├── raw_instrument_code (TEXT - ticker from file, e.g., "AFI")
├── raw_transaction_type (TEXT - BUY/SELL/etc from file)
├── raw_quantity (TEXT - unparsed quantity)
├── raw_price (TEXT - unparsed price)
├── raw_currency (TEXT - if provided in file)
├── processed_flag (BOOLEAN - FALSE until moved to fact tables)
├── validation_errors (TEXT - JSON of any validation issues)
└── import_timestamp (audit trail)
```

**CRITICAL FIELD ANALYSIS**:
- **raw_total_value**: REMOVED - can be calculated as quantity * price in fact table
- **All raw fields as TEXT**: Preserves original data for debugging/audit
- **processed_flag**: Prevents double-processing, enables retry logic
- **import_batch_id**: Enables atomic rollback of entire import

**Stage 2: Dimension Population**
```sql
DIM_STOCK (one record per unique instrument across all portfolios)
├── stock_key (PK, auto-increment)
├── instrument_code (UNIQUE - "AFI") 
├── yahoo_symbol (UNIQUE - "AFI.AX" after market assignment)
├── name (NULL until verified via Yahoo Finance)
├── market_key (FK to DIM_YAHOO_MARKET_CODES)
├── currency (NULL until verified via Yahoo Finance)  
├── verification_status ('pending'/'verified'/'failed'/'delisted')
├── sector/industry/exchange (populated during full verification)
└── last_updated (when verification status changed)

PORTFOLIO_STOCK_CONFIG (portfolio-specific stock settings)
├── config_key (PK)
├── portfolio_key (FK) 
├── stock_key (FK)
├── drp_enabled (BOOLEAN - dividend reinvestment plan)
└── notes (TEXT - user notes)
```

**CRITICAL DESIGN DECISIONS**:
- **Global vs Portfolio-Specific Stocks**: DIM_STOCK is global (one "AFI" across all portfolios), PORTFOLIO_STOCK_CONFIG handles portfolio-specific settings
- **Verification Status**: Stock-level, not portfolio-level (once verified, verified for all portfolios)
- **Market Assignment**: Required before moving to fact tables

**Stage 3: Fact Table Population**
```sql  
FACT_TRANSACTIONS (final transaction records)
├── transaction_key (PK)
├── stock_key (FK to DIM_STOCK)
├── portfolio_key (FK to DIM_PORTFOLIO)  
├── transaction_type_key (FK to DIM_TRANSACTION_TYPE)
├── date_key (FK to DIM_DATE - for analytics)
├── transaction_date (actual date)
├── quantity (DECIMAL - parsed and validated)
├── price (DECIMAL - parsed and validated) 
├── total_value (CALCULATED - quantity * price)
├── original_currency/exchange_rate (multi-currency support)
└── total_value_base (converted to portfolio base currency)
```

**Stage 4: Position Calculation**
```sql
PORTFOLIO_POSITIONS (current position snapshots)  
├── position_key (PK)
├── portfolio_key (FK)
├── stock_key (FK)
├── current_quantity (sum of all transactions)
├── average_cost (weighted average of buy transactions)
├── total_cost (current_quantity * average_cost)
├── current_price (latest market price)
├── current_value (current_quantity * current_price)
├── unrealized_pl (current_value - total_cost)
└── last_updated (when position recalculated)
```

#### Database Flow State Transitions

**Question: What happens when stock gets verified?**
```
DIM_STOCK: verification_status = 'pending' → 'verified'
├── name = populated from Yahoo Finance
├── currency = populated from Yahoo Finance  
└── last_updated = current timestamp
Action: Ready for fact table processing
```

**Question: What if stock stays unverified and user wants to skip?**
```
Option 1: Mark as delisted
├── DIM_STOCK: verification_status = 'delisted'
└── Action: Can proceed to fact table processing

Option 2: Skip in current import
├── STG_RAW_TRANSACTIONS: processed_flag = remains FALSE
└── Action: Transactions stay in staging for next import attempt
```

**Question: What happens next time user imports?**
```
Existing stocks:
├── Check if already exists in DIM_STOCK by instrument_code
├── If exists: Use existing stock_key for fact table
└── If verification_status = 'failed': Re-attempt verification

New stocks:  
├── Create new DIM_STOCK record with 'pending' status
└── Require market assignment + verification before fact table processing

Duplicate transactions:
├── Compare against existing FACT_TRANSACTIONS
├── Match on: portfolio_key, stock_key, date, quantity, price, transaction_type
└── Skip duplicates, process only new transactions
```

#### Schema Optimization Analysis

**Fields that can be removed/calculated**:
- **raw_total_value**: Remove from STG_RAW_TRANSACTIONS (calculate in fact table)
- **total_value in FACT_TRANSACTIONS**: Calculate as quantity * price
- **current_value in PORTFOLIO_POSITIONS**: Calculate as current_quantity * current_price

**Fields that need addition**:
- **DIM_STOCK.last_verified**: Track when verification last attempted
- **DIM_STOCK.verification_attempts**: Count failed verification attempts
- **STG_RAW_TRANSACTIONS.skip_reason**: Why transaction was skipped (duplicate/delisted/failed)

#### Error Handling & Recovery Patterns

**Atomic Import Process**:
```
BEGIN TRANSACTION
├── Validate all raw data in staging
├── Resolve all stock market assignments  
├── Verify all new stocks (or mark delisted)
├── Process all transactions to fact tables
├── Update all portfolio positions
├── Mark raw transactions as processed
└── COMMIT or ROLLBACK (all-or-nothing)
```

**Retry Logic**:
- Failed imports leave data in staging (processed_flag = FALSE)
- Next import can retry same data or add new data
- User can fix market assignments and re-attempt verification
- Duplicate detection prevents double-processing successful transactions

#### Error Fixes Applied
1. **Infinite Re-render in ColumnMapping**: Fixed by creating `isValidMapping()` pure function instead of calling stateful `validateMapping()` in render cycle
2. **TypeScript ReactNode Error**: Fixed by wrapping column values with `String()` conversion
3. **CSS Layout Conflicts**: Removed conflicting padding/max-width from stock-management.css
4. **API Endpoint Duplicates**: Fixed duplicate function definitions in import_transactions.py

---

## 3. FRONTEND ARCHITECTURE

### Component Structure
```
src/components/
├── import/
│   ├── FileUpload.tsx              ✅ Working
│   ├── ColumnMapping.tsx           ✅ Working (Fixed infinite render)
│   ├── DataPreview.tsx             🔄 Needs update for confirmation
│   └── StockMarketAssignment.tsx   ❌ To be created
├── stock-management/
│   └── StockManagement.tsx         ✅ Working
└── portfolio/
    └── PortfolioView.tsx           ✅ Working
```

### CSS Architecture
- **CSS Variables**: Used for consistent theming across components
- **Component-specific CSS**: Each major component has its own CSS file
- **Layout System**: Grid and flexbox based, responsive design
- **LESSON LEARNED**: Avoid conflicting layout styles (padding/max-width) in component CSS when components are used within existing layouts

### State Management
- **React useState**: For local component state
- **Props drilling**: For data flow between import workflow components
- **Future consideration**: Context API if state management becomes complex

---

## 4. BACKEND ARCHITECTURE

### API Structure
```
app/api/
├── import_transactions.py     🔄 Main import workflow APIs
├── market_data.py            ✅ Stock verification and market data
├── portfolios.py             ✅ Portfolio CRUD operations
├── stocks.py                 ✅ Stock management
└── transactions.py           ✅ Transaction operations
```

### Critical API Endpoints

#### Import Workflow APIs
- `GET /api/import/template` - Download CSV template
- `POST /api/import/analyze` - Analyze uploaded file structure  
- `POST /api/import/validate` - Confirm raw data quality (NO Yahoo API calls)
- `GET /api/import/markets` - Get available market codes for assignment
- `POST /api/import/assign-markets` - Assign markets to stocks with verification
- `POST /api/import/transactions` - Final import processing

#### Market Data APIs  
- `POST /api/market-data/verify-stock` - Full stock verification with Yahoo Finance
- `GET /api/market-data/current-price/<stock_id>` - Get current stock price
- `POST /api/market-data/bulk-update` - Update multiple stocks

### Service Layer Architecture

#### TransactionImportService
- **File Processing**: CSV/Excel reading with pandas
- **Column Mapping**: Intelligent detection and user customization
- **Raw Data Confirmation**: Quality validation without external APIs
- **Staging Process**: STG_RAW_TRANSACTIONS for batch processing
- **ETL Pipeline**: Extract → Transform → Load with error handling

#### MarketDataService  
- **Yahoo Finance Integration**: yfinance library for market data
- **Lightweight Verification**: `verify_stock_lightweight()` for assignment workflow
- **Full Verification**: `verify_and_create_stock()` for complete stock validation
- **Currency Conversion**: Multi-currency support with cross-rates

### Database Models (Kimball Star Schema)

#### Dimension Tables
- **DIM_STOCK**: Stock master data with market assignments
- **DIM_PORTFOLIO**: Portfolio definitions with portfolio-first paradigm
- **DIM_TRANSACTION_TYPE**: Transaction types (BUY, SELL, DIVIDEND, etc.)
- **DIM_YAHOO_MARKET_CODES**: 87 Yahoo Finance market codes with suffixes
- **DIM_DATE**: Date dimension for analytics

#### Fact Tables
- **FACT_TRANSACTIONS**: All transaction data with foreign keys to dimensions
- **PORTFOLIO_POSITIONS**: Current position snapshots with P&L calculations

#### Configuration Tables
- **PORTFOLIO_STOCK_CONFIG**: Portfolio-specific stock settings (DRP flags, notes)

#### Staging Tables
- **STG_RAW_TRANSACTIONS**: Import staging with batch processing support

---

## 5. DATA IMPORT PHILOSOPHY & REQUIREMENTS

### User Control Principles
1. **Transparency**: User sees exactly what data will be imported
2. **Verification**: User controls all market assignments and validations  
3. **Error Handling**: Clear error messages with actionable guidance
4. **Flexibility**: Support for various file formats and column arrangements
5. **Performance**: Staged processing to handle large datasets efficiently

### Market Assignment Strategy
- **87 Yahoo Markets**: Complete coverage of global exchanges
- **User Selection**: Users explicitly choose markets for new stocks
- **Intelligent Suggestions**: System suggests likely markets based on instrument codes
- **Verification Integration**: Immediate validation of market + stock combinations
- **Error Recovery**: Clear feedback when assignments fail with retry options

### Data Quality Standards
- **Duplicate Detection**: Exact match checking against existing portfolio transactions
- **Format Validation**: Date, numeric, and text field validation
- **Required Field Enforcement**: Clear messaging for missing critical data
- **Error Aggregation**: Batch error reporting for efficient correction

---

## 6. CURRENT IMPLEMENTATION STATUS

### Phase 1: Database Schema Updates ✅ COMPLETED
- [x] Copy DIM_YAHOO_MARKET_CODES from yahoo_market_codes.txt to schema.sql
- [x] Add PORTFOLIO_STOCK_CONFIG table to schema.sql  
- [x] Modify DIM_STOCK to add market_key column
- [x] Remove raw_total_value from STG_RAW_TRANSACTIONS
- [x] Delete yahoo_market_codes.txt file after copying

### Phase 2: Backend API Development 🔄 IN PROGRESS  
- [x] 2.1 Fix 'Confirm Raw Data' step - add confirm_raw_data method
- [x] 2.2 Create stock market assignment APIs
- [ ] 2.3 Modify final import process

### Phase 3: Frontend UI Development ❌ PENDING
- [ ] 3.1 Update DataPreview component for confirmation
- [ ] 3.2 Create StockMarketAssignment component

---

## 7. RECENT TRANSACTION IMPORT FIXES (July 2025)

### CRITICAL: Flask Blueprint Registration Issues  
- **Problem**: Multiple duplicate endpoint definitions causing Flask AssertionError: "View function mapping is overwriting an existing endpoint function: api.import_transaction"
- **Root Cause**: Used `replace_all=True` on error handler pattern, creating 4 duplicate `import_transactions()` functions at lines 39, 142, 402, 629
- **Symptoms**: Backend completely unable to start, ECONNREFUSED errors in frontend
- **Solution**: Manually rewrote entire `import_transactions.py` file with clean endpoint structure
- **Final Endpoints**: 6 clean routes with no duplicates:
  - `GET /import/template` - CSV template download
  - `GET /import/markets` - Available market codes  
  - `POST /import/assign-markets` - Market assignment + verification
  - `POST /import/analyze` - File structure analysis
  - `POST /import/validate` - Raw data validation
  - `POST /import/transactions` - Final import processing
- **CRITICAL LEARNING**: NEVER use `replace_all=True` on common patterns like error handlers - always target specific unique strings or rewrite manually

### Missing API Endpoints (404 Errors)
- **Problem**: Frontend calling `/api/import/validate` but endpoint didn't exist
- **Cause**: Frontend-backend API contract mismatch during development
- **Solution**: Add missing endpoint with proper request/response handling
- **File**: `import_transactions.py:233-378` - added `/import/validate` endpoint

### Content-Type Mismatch (415 Errors)  
- **Problem**: Frontend sending FormData, backend expecting JSON
- **Root Cause**: Frontend sends file uploads directly to validate endpoint
- **Solution**: Update backend to handle both FormData (file uploads) and JSON (staged data)
- **File**: `import_transactions.py:237-378` - dual handling for different request types
- **Learning**: Always align frontend request format with backend expectations

### Transaction Import UI Flow Restructuring
- **Problem**: Date format selection in wrong component, validation errors not displayed properly
- **Changes Made**:
  - **Moved date format selection** from DataPreview to ColumnMapping component
  - **Fixed backend validation** to return structured results instead of 400 errors
  - **Renamed step** from "Preview & Validate" to "Confirm Transactions"
  - **Updated component flow** to pass dateFormat through entire chain
- **Files**: 
  - `ColumnMapping.tsx:26-37, 273-302` - added date format selection
  - `TransactionImport.tsx:76-77` - renamed step
  - `import_transactions.py:311-322` - fixed validation response structure
- **Learning**: UI flow should match user mental model, not technical implementation convenience

### Backend Validation Response Structure
- **Problem**: Backend returned 400 errors when validation failed, frontend expected structured data
- **Solution**: Always return 200 with structured validation results containing both errors and successes
- **Pattern**: 
  ```python
  return jsonify({
      'success': True,
      'data': {
          'total_rows': total,
          'valid_rows': valid_count, 
          'validation_errors': error_list,
          'validated_transactions': valid_data
      }
  })
  ```
- **Learning**: Validation endpoints should return validation results, not errors

### Frontend Webpack Deprecation Warnings (Non-Critical)
- **Warning 1**: `[DEP0060] DeprecationWarning: The 'util._extend' API is deprecated. Please use Object.assign() instead.`
- **Warning 2**: `[DEP_WEBPACK_DEV_SERVER_ON_AFTER_SETUP_MIDDLEWARE] DeprecationWarning: 'onAfterSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.`  
- **Warning 3**: `[DEP_WEBPACK_DEV_SERVER_ON_BEFORE_SETUP_MIDDLEWARE] DeprecationWarning: 'onBeforeSetupMiddleware' option is deprecated. Please use the 'setupMiddlewares' option.`
- **Impact**: Non-blocking warnings, application functions normally
- **Cause**: Outdated webpack dev server configuration in React app
- **Status**: Low priority - does not affect functionality
- **Solution**: Update webpack dev server configuration or React Scripts version when convenient

### Error Resolution Summary (July 5, 2025)
**FIXED** ✅:
1. Flask AssertionError (duplicate endpoints) - **BLOCKING** - Backend startup failure
2. ECONNREFUSED (backend connection) - **HIGH** - Frontend unable to connect
3. Missing `/api/import/validate` endpoint - **HIGH** - Step 3 validation failure  
4. Content-Type mismatch (415 errors) - **HIGH** - Frontend/backend API contract

**REMAINING** ⚠️:
1. Webpack deprecation warnings - **LOW** - Non-blocking, cosmetic only

---

## 8. LESSONS LEARNED & DEBUGGING NOTES

### React Performance Issues
- **Infinite Renders**: Caused by calling stateful functions during render cycle
- **Solution**: Create pure validation functions that can be safely called during render
- **File**: ColumnMapping.tsx:87 - `isValidMapping()` function

### CSS Layout Conflicts  
- **Issue**: Component-specific padding/max-width conflicting with page layouts
- **Solution**: Remove layout styles from component CSS, handle layout at page level
- **File**: stock-management.css - removed conflicting styles

### API Endpoint Conflicts
- **Issue**: Duplicate function names when using replace_all operations
- **Solution**: Careful manual cleanup of duplicate endpoints
- **File**: import_transactions.py - cleaned up duplicate functions

### TypeScript ReactNode Issues
- **Issue**: `Type 'unknown' is not assignable to type 'ReactNode'`
- **Solution**: Explicit type conversion with `String()` wrapper
- **File**: DataPreview.tsx:78 - `{String(column)}` instead of `{column}`

---

## 8. FUTURE DEVELOPMENT PRIORITIES

### Immediate Next Steps
1. **Complete Phase 2.3**: Modify final import process to use new workflow
2. **Implement Phase 3**: Frontend components for confirmation and market assignment
3. **User Testing**: Validate complete workflow with real transaction files
4. **Error Handling**: Enhance error reporting and recovery mechanisms

### Medium-term Enhancements  
1. **Batch Processing**: Support for very large transaction files
2. **Import Templates**: Save and reuse column mappings for regular imports
3. **Market Intelligence**: Automatic market suggestions based on instrument code patterns
4. **Audit Trail**: Complete logging of all import activities

### Long-term Vision
1. **Multi-Portfolio Import**: Import transactions across multiple portfolios simultaneously
2. **Data Validation Rules**: User-configurable validation rules for data quality
3. **Import Scheduling**: Automated imports from external systems
4. **Advanced Analytics**: Portfolio performance metrics based on imported data

---

## 9. CRITICAL CONFIGURATION & DEPLOYMENT NOTES

### Environment Setup
- **Python Version**: 3.12+ required for backend
- **Node Version**: 18+ required for frontend  
- **Database**: SQLite with WAL mode for concurrent access
- **External Dependencies**: yfinance, pandas, flask, react

### File Structure Requirements
- **Upload Directory**: Ensure proper permissions for file upload handling
- **Temp Storage**: Sufficient space for processing large CSV/Excel files
- **Log Files**: Structured logging for debugging import processes

### Performance Considerations
- **Chunked Processing**: Large files processed in batches to avoid memory issues
- **Database Indexing**: Critical indexes on portfolio_key, stock_key, and date fields
- **API Rate Limits**: Yahoo Finance API calls throttled to avoid rate limiting
- **Caching Strategy**: Market code lookups cached to improve performance

---

## 10. USER INTERFACE REQUIREMENTS & PHILOSOPHY

### Import Workflow UX Design
- **Progressive Disclosure**: Show information in logical steps without overwhelming users
- **Clear Navigation**: Always show current step and allow going back to previous steps
- **Error Prevention**: Validate data early and clearly indicate issues
- **Success Feedback**: Clear confirmation of successful operations with summary details

### Data Presentation Standards
- **Tabular Data**: Use consistent table formatting with sorting and filtering
- **Error Highlighting**: Red highlighting for errors, yellow for warnings
- **Progress Indicators**: Show progress during long-running operations
- **Responsive Design**: Work effectively on desktop and tablet devices

### Accessibility Requirements
- **Keyboard Navigation**: All functionality accessible via keyboard
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **Color Contrast**: Meet WCAG 2.1 AA standards for color contrast
- **Error Messaging**: Clear, descriptive error messages for all validation failures

---

**DOCUMENT MAINTENANCE**: This document should be updated with every significant change to the application. Key sections to maintain:
- Update implementation status when features are completed
- Add new lessons learned when debugging issues
- Capture user feedback and requirement changes  
- Document any architectural decisions or technical debt
- Record performance optimization decisions and results

**LAST UPDATED**: 2025-01-04 - Phase 2.2 (Stock Market Assignment APIs) completed
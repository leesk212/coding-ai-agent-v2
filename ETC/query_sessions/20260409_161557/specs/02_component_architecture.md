# Component Architecture Specification

## Architecture Overview

The PMS frontend follows a feature-based component organization with a clear separation of concerns:
- **Presentational Components**: Pure UI components focused on rendering
- **Container Components**: Logic and state management components
- **Layout Components**: Page structure and navigation
- **Shared Components**: Reusable UI elements across the application

## Component Tree Structure

```
App
├── Providers
│   ├── ThemeProvider (MUI)
│   ├── ReduxProvider
│   ├── QueryClientProvider (RTK Query)
│   ├── AuthProvider
│   └── ToastProvider
├── Router
└── Routes
    ├── Public Routes
    │   └── AuthLayout
    │       ├── LoginPage
    │       ├── RegistrationPage
    │       └── PasswordResetPage
    └── Protected Routes
        └── MainLayout
            ├── Sidebar
            ├── Header
            └── MainContent
                ├── Dashboard
                ├── Projects
                │   ├── ProjectList
                │   ├── ProjectDetail
                │   └── ProjectForm
                ├── GanttChartView
                ├── AdminPanel
                │   ├── AdminDashboard
                │   ├── UserManagement
                │   └── SystemStats
                └── NotFound
```

## Component Hierarchies

### 1. Authentication Components

```
AuthLayout
├── AuthCard
│   ├── AuthHeader
│   ├── AuthForm
│   └── AuthFooter
└── BackgroundDecoration

LoginPage
├── LoginForm
│   ├── EmailInput
│   ├── PasswordInput
│   ├── RememberMeCheckbox
│   ├── SubmitButton
│   └── ForgotPasswordLink
└── SocialLogin (optional)

RegistrationPage
├── RegistrationForm
│   ├── FullNameInput
│   ├── EmailInput
│   ├── PasswordInput
│   ├── ConfirmPasswordInput
│   ├── TermsAgreement
│   └── SubmitButton
└── TermsAndConditionsModal

PasswordResetPage
├── PasswordResetForm
│   ├── EmailInput
│   └── SubmitButton
└── PasswordResetInstructions
```

### 2. Layout Components

```
MainLayout
├── Sidebar
│   ├── Logo
│   ├── NavigationMenu
│   │   ├── NavItem
│   │   │   ├── Icon
│   │   │   ├── Label
│   │   │   └── Submenu
│   │   └── SectionDivider
│   └── UserMenu
│       ├── Avatar
│       ├── UserName
│       └── MenuItem
├── Header
│   ├── SearchBar
│   ├── Notifications
│   ├── Breadcrumbs
│   └── UserMenu
└── MainContent
    └── PageContainer
        ├── PageHeader
        │   ├── Title
        │   ├── Actions
        │   └── BackButton
        └── PageContent
```

### 3. Dashboard Components

```
Dashboard
├── StatsGrid
│   ├── StatCard
│   │   ├── StatIcon
│   │   ├── StatLabel
│   │   ├── StatValue
│   │   └── TrendIndicator
│   └── StatCard (x4)
├── ProjectOverviewChart
│   ├── ChartContainer
│   ├── ChartCanvas
│   ├── Legend
│   └── TimeRangeSelector
├── RecentActivities
│   ├── ActivityFeed
│   │   └── ActivityItem
│   │       ├── ActivityIcon
│   │       ├── ActivityDescription
│   │       ├── ActivityMetadata
│   │       └── ActivityAction
│   └── ViewAllButton
└── QuickActions
    ├── QuickActionButton
    │   ├── ActionIcon
    │   ├── ActionLabel
    │   └── Tooltip
    └── QuickActionButton (x4)
```

### 4. Project Management Components

```
ProjectList
├── ProjectListToolbar
│   ├── SearchBar
│   ├── FilterBar
│   │   ├── StatusFilter
│   │   ├── PriorityFilter
│   │   └── DateRangeFilter
│   ├── ViewToggle
│   │   ├── TableView
│   │   └── GridView
│   └── CreateProjectButton
├── ProjectTable (tableView)
│   ├── TableHeader
│   │   └── SortableColumnHeader
│   ├── TableRow
│   │   ├── ProjectRow
│   │   │   ├── ProjectName
│   │   │   ├── ProjectStatus
│   │   │   ├── ProjectProgress
│   │   │   ├── TeamMembers
│   │   │   └── Actions
│   │   └── SortableColumnHeader
│   └── TableFooter
│       └── Pagination
├── ProjectGrid (gridView)
│   └── GridContainer
│       └── ProjectCard
│           ├── ProjectHeader
│           │   ├── ProjectTitle
│           │   ├── StatusBadge
│           │   └── PriorityBadge
│           ├── ProjectBody
│           │   ├── ProgressBar
│           │   ├── TeamAvatars
│           │   └── DueDate
│           └── CardActions
└── EmptyState

ProjectForm
├── FormHeader
│   ├── FormTitle
│   └── FormActions
├── FormTabs
│   ├── Tab
│   └── TabPanel
├── ProjectInfoSection
│   ├── ProjectNameInput
│   ├── DescriptionInput
│   ├── ProjectCodeInput
│   └── ColorPicker
├── TimelineSection
│   ├── StartDatePicker
│   ├── EndDatePicker
│   └── DurationDisplay
├── TeamSection
│   ├── TeamMembersList
│   │   └── TeamMemberChip
│   │       ├── Avatar
│   │       ├── Name
│   │       └── Role
│   └── AddTeamMemberButton
├── BudgetSection
│   ├── BudgetInput
│   └── CurrencySelector
├── SettingsSection
│   └── Toggle
└── FormFooter
    ├── CancelButton
    └── SaveButton

ProjectDetail
├── ProjectHeader
│   ├── ProjectTitle
│   ├── StatusDropdown
│   ├── PriorityDropdown
│   └── ActionButtons
├── ProjectTabs
│   ├── OverviewTab
│   ├── TasksTab
│   ├── TimelineTab
│   └── SettingsTab
├── OverviewTabContent
│   ├── ProjectInfoCard
│   ├── ProjectStats
│   └── TeamSection
├── TasksTabContent
│   ├── TaskList
│   ├── TaskFilters
│   └── TaskActions
├── TimelineTabContent
│   └── TimelineView
└── SettingsTabContent
    └── ProjectSettings
```

### 5. Gantt Chart Components

```
GanttChartView
├── GanttToolbar
│   ├── ZoomLevelSelector
│   ├── TimelineViewToggle
│   ├── DateNavigator
│   └── FilterBar
├── GanttChart
│   ├── GanttCanvas
│   ├── GanttHeader
│   ├── GanttBody
│   └── GanttFooter
├── TaskDetailsPanel
└── GanttControls

GanttChart Component (DHTMLX Gantt)
├── GanttTimeline
│   ├── TimelineHeader
│   │   └── TimelineCells
│   │       ├── DayCell
│   │       ├── WeekCell
│   │       └── MonthCell
│   └── TimelineContent
│       └── GanttRows
│           ├── GanttRow
│           │   ├── TaskNode
│           │   │   ├── TaskBar
│           │   │   ├── TaskMilestone
│           │   │   ├── TaskProgress
│           │   │   ├── TaskCheckbox
│           │   │   └── TaskDragHandle
│           │   ├── TaskDependencies
│           │   │   └── DependencyLines
│           │   └── TaskChildren
│           │       └── SubTasks
│           │           └── GanttRow (recursive)
│           └── TaskLinks
│               └── LinkLines
├── GanttContextMenu
│   └── ContextMenuItem
└── GanttTooltip
```

### 6. Admin Panel Components

```
AdminPanel
├── AdminDashboard
│   ├── SystemOverview
│   │   └── StatCard (system stats)
│   ├── RecentRegistrations
│   ├── ActiveProjectsOverview
│   └── SystemHealth
├── UserManagement
│   ├── UserToolbar
│   │   ├── SearchBar
│   │   ├── RoleFilter
│   │   ├── StatusFilter
│   │   └── AddUserButton
│   ├── UserTable
│   │   ├── TableHeader
│   │   ├── TableRow
│   │   │   └── UserRow
│   │   │       ├── UserAvatar
│   │   │       ├── UserName
│   │   │       ├── UserEmail
│   │   │       ├── UserRole
│   │   │       ├── UserStatus
│   │   │       └── UserActions
│   │   └── TableFooter
│   └── UserDetailModal
│       ├── UserSummary
│       ├── UserDetails
│       ├── UserRoles
│       └── UserActions
├── SystemStats
│   ├── StatsCharts
│   │   ├── UserGrowthChart
│   │   ├── ProjectStatsChart
│   │   └── ActivityChart
│   └── DataTables
│       ├── UserActivityTable
│       └── SystemLogTable
└── SettingsManagement
    ├── SettingsSection
    └── SettingsForm
```

## Shared Components

### Form Components
```
BaseInput
├── InputLabel
├── InputWrapper
│   ├── Input
│   ├── InputPrefix
│   ├── InputSuffix
│   └── HelperText
└── ErrorText

BaseSelect
├── SelectLabel
├── SelectWrapper
│   ├── Select
│   └── SelectIcon
└── HelperText

BaseTextarea
├── TextareaLabel
├── TextareaWrapper
│   └── Textarea
└── HelperText

BaseCheckbox
├── CheckboxWrapper
│   ├── Checkbox
│   └── Label
└── HelperText

BaseRadio
├── RadioGroup
│   └── Radio
└── HelperText

BaseDatePicker
├── DatePickerLabel
├── DatePickerWrapper
│   └── DatePicker
└── HelperText

BaseFileUpload
├── FileUploadLabel
├── FileDropzone
│   ├── DropzoneIndicator
│   └── FilePreviewList
│       └── FilePreview
│           ├── FileIcon
│           ├── FileName
│           └── RemoveButton
└── HelperText
```

### Display Components
```
StatusBadge
├── Badge
├── StatusIcon
└── StatusLabel

PriorityBadge
├── Badge
└── PriorityLabel

Avatar
├── AvatarImage
├── AvatarInitials
└── AvatarStatus

ProgressBar
├── ProgressBarContainer
│   ├── ProgressBarFill
│   └── ProgressLabel
└── ProgressInfo

Card
├── CardHeader
│   ├── CardTitle
│   ├── CardSubheader
│   └── CardActions
├── CardMedia
│   └── MediaContent
├── CardContent
└── CardActions

Button
├── Button
├── ButtonIcon
└── ButtonLabel

Tooltip
├── TooltipContainer
└── TooltipContent

Modal
├── ModalOverlay
├── ModalContainer
│   ├── ModalHeader
│   │   ├── ModalTitle
│   │   └── ModalClose
│   ├── ModalContent
│   └── ModalFooter
└── ModalBackdrop

Toast
├── ToastContainer
│   └── ToastItem
│       ├── ToastIcon
│       ├── ToastMessage
│       ├── ToastTitle
│       └── ToastAction

LoadingOverlay
├── Overlay
└── LoadingSpinner

EmptyState
├── EmptyIcon
├── EmptyTitle
├── EmptyDescription
└── EmptyAction

Skeleton
├── SkeletonContainer
└── SkeletonShape

Tabs
├── TabList
│   ├── Tab
│   └── TabIndicator
├── TabPanels
│   └── TabPanel
└── TabContext

Table
├── TableHeader
│   └── SortableHeader
├── TableBody
│   └── TableRow
│       └── TableCell
├── TableFooter
│   └── Pagination
└── TableContext

Dialog
├── DialogOverlay
├── DialogContainer
│   ├── DialogHeader
│   ├── DialogContent
│   └── DialogFooter
└── DialogBackdrop

Badge
├── Badge
└── BadgeContent

Chip
├── Chip
│   ├── ChipIcon
│   ├── ChipLabel
│   └── ChipDelete
└── ChipContext
```

### Feedback Components
```
Snackbar
├── SnackbarContainer
│   └── SnackbarItem
│       ├── SnackbarIcon
│       ├── SnackbarMessage
│       ├── SnackbarTitle
│       └── SnackbarAction

Alert
├── AlertContainer
│   ├── AlertIcon
│   ├── AlertTitle
│   └── AlertMessage
└── AlertAction

ConfirmDialog
├── ConfirmDialogContainer
│   ├── ConfirmDialogTitle
│   ├── ConfirmDialogContent
│   └── ConfirmDialogFooter
└── ConfirmDialogBackdrop

Confirm
├── ConfirmContainer
│   ├── ConfirmIcon
│   ├── ConfirmTitle
│   ├── ConfirmMessage
│   └── ConfirmFooter
└── ConfirmBackdrop

ConfirmDialog
├── ConfirmDialogContainer
│   ├── ConfirmDialogTitle
│   ├── ConfirmDialogContent
│   └── ConfirmDialogFooter
└── ConfirmDialogBackdrop
```

## Component Props Specifications

### Base Component Props (Shared)

```typescript
interface BaseProps {
  /** Additional CSS classes */
  className?: string;
  /** Unique identifier */
  id?: string;
  /** Test identifier for E2E testing */
  'data-testid'?: string;
  /** Component title for accessibility */
  'aria-label'?: string;
}

interface ButtonProps extends BaseProps {
  /** Button variant */
  variant?: 'text' | 'outlined' | 'contained' | 'ghost';
  /** Button size */
  size?: 'small' | 'medium' | 'large';
  /** Button color */
  color?: 'primary' | 'secondary' | 'error' | 'warning' | 'success' | 'info';
  /** Whether button is loading */
  loading?: boolean;
  /** Whether button is disabled */
  disabled?: boolean;
  /** Full width button */
  fullWidth?: boolean;
  /** Start icon */
  startIcon?: React.ReactNode;
  /** End icon */
  endIcon?: React.ReactNode;
  /** Button click handler */
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  /** Button submit handler */
  onSubmit?: (event: React.FormEvent<HTMLFormElement>) => void;
}

interface InputProps extends BaseProps {
  /** Input label */
  label?: string;
  /** Input name */
  name: string;
  /** Input type */
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  /** Input value */
  value?: string | number;
  /** Input placeholder */
  placeholder?: string;
  /** Whether input is required */
  required?: boolean;
  /** Whether input is disabled */
  disabled?: boolean;
  /** Whether input is readonly */
  readOnly?: boolean;
  /** Error message */
  error?: string;
  /** Helper text */
  helperText?: string;
  /** Input change handler */
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
  /** Input blur handler */
  onBlur?: (event: React.FocusEvent<HTMLInputElement>) => void;
  /** Input focus handler */
  onFocus?: (event: React.FocusEvent<HTMLInputElement>) => void;
  /** Input validation */
  validate?: (value: string | number) => string | undefined;
}
```

### Navigation Props

```typescript
interface NavigationItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  children?: NavigationItem[];
  badge?: {
    count: number;
    color?: 'primary' | 'secondary' | 'error';
  };
  canAccess?: boolean;
}

interface SidebarProps extends BaseProps {
  /** Navigation items */
  items: NavigationItem[];
  /** Currently active path */
  activePath: string;
  /** Whether sidebar is collapsed */
  collapsed?: boolean;
  /** Sidebar collapse handler */
  onCollapse?: (collapsed: boolean) => void;
  /** Navigation item click handler */
  onNavigate?: (path: string) => void;
}

interface HeaderProps extends BaseProps {
  /** Page title */
  title?: string;
  /** Breadcrumb items */
  breadcrumbs?: { label: string; path?: string }[];
  /** Search query */
  searchQuery?: string;
  /** Search change handler */
  onSearch?: (query: string) => void;
  /** Notification count */
  notificationCount?: number;
  /** User profile */
  user?: {
    name: string;
    avatar?: string;
  };
  /** User menu items */
  menuItems?: Array<{
    label: string;
    icon: React.ReactNode;
    onClick?: () => void;
    divider?: boolean;
  }>;
}
```

### Project Props

```typescript
interface Project {
  id: string;
  name: string;
  code: string;
  description: string;
  status: 'active' | 'completed' | 'on_hold' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  progress: number;
  startDate: string;
  endDate: string;
  budget?: number;
  currency: string;
  team: TeamMember[];
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

interface TeamMember {
  id: string;
  name: string;
  avatar?: string;
  role: string;
  email: string;
}

interface ProjectFormValues {
  name: string;
  code: string;
  description: string;
  status: Project['status'];
  priority: Project['priority'];
  startDate: string;
  endDate: string;
  budget?: number;
  currency: string;
  teamIds: string[];
  color: string;
}

interface ProjectListProps extends BaseProps {
  /** Projects to display */
  projects: Project[];
  /** Loading state */
  loading?: boolean;
  /** View mode: 'table' | 'grid' */
  viewMode?: 'table' | 'grid';
  /** Pagination info */
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
  };
  /** Filters */
  filters?: {
    status?: string;
    priority?: string;
    search?: string;
    dateRange?: { start: string; end: string };
  };
  /** Project click handler */
  onProjectClick?: (projectId: string) => void;
  /** Create project handler */
  onCreateProject?: () => void;
  /** Edit project handler */
  onEditProject?: (projectId: string) => void;
  /** Delete project handler */
  onDeleteProject?: (projectId: string) => void;
  /** Pagination change handler */
  onPaginationChange?: (page: number, pageSize: number) => void;
  /** Filter change handler */
  onFilterChange?: (filters: Record<string, string>) => void;
}

interface ProjectDetailProps extends BaseProps {
  /** Project data */
  project: Project;
  /** Loading state */
  loading?: boolean;
  /** Edit mode */
  editable?: boolean;
  /** Project update handler */
  onUpdateProject?: (project: Partial<Project>) => void;
  /** Project delete handler */
  onDeleteProject?: () => void;
  /** Tasks for this project */
  tasks?: Task[];
}

interface ProjectFormProps extends BaseProps {
  /** Project data (for edit mode) */
  project?: Project;
  /** Submit handler */
  onSubmit?: (values: ProjectFormValues) => void;
  /** Cancel handler */
  onCancel?: () => void;
  /** Submit in progress */
  submitting?: boolean;
}
```

### Gantt Chart Props

```typescript
interface GanttTask {
  id: string;
  text: string;
  start_date: Date | string;
  duration: number;
  progress: number;
  parent?: string;
  open?: boolean;
  color?: string;
  type?: 'task' | 'milestone' | 'project';
  resource?: string;
  deps?: string[];
  custom_css?: string;
}

interface GanttChartProps extends BaseProps {
  /** Gantt tasks */
  tasks: GanttTask[];
  /** Gantt projects (groups) */
  projects?: GanttTask[];
  /** Dependencies */
  links?: Array<{ id: string; source: string; target: string; type?: string }>;
  /** Resources */
  resources?: Array<{ id: string; text: string; color: string }>;
  /** Loading state */
  loading?: boolean;
  /** View mode: 'day' | 'week' | 'month' */
  viewMode?: 'day' | 'week' | 'month';
  /** Selected task */
  selectedTask?: string;
  /** Whether read-only */
  readOnly?: boolean;
  /** Task click handler */
  onTaskClick?: (taskId: string) => void;
  /** Task drag handler */
  onTaskDrag?: (taskId: string, newStart: Date, newDuration: number) => void;
  /** Task change handler */
  onTaskChange?: (taskId: string, changes: Partial<GanttTask>) => void;
  /** Task create handler */
  onTaskCreate?: (task: GanttTask) => void;
  /** Task delete handler */
  onTaskDelete?: (taskId: string) => void;
  /** Link create handler */
  onLinkCreate?: (link: { source: string; target: string }) => void;
  /** Link delete handler */
  onLinkDelete?: (linkId: string) => void;
  /** View mode change handler */
  onViewModeChange?: (mode: 'day' | 'week' | 'month') => void;
  /** Timeline navigation */
  onNavigate?: (date: Date) => void;
  /** Zoom level */
  zoomLevel?: number;
  /** Show dependencies */
  showDependencies?: boolean;
  /** Show milestones */
  showMilestones?: boolean;
  /** Show critical path */
  showCriticalPath?: boolean;
}

interface GanttTaskNodeProps extends BaseProps {
  /** Task data */
  task: GanttTask;
  /** Whether task is selected */
  selected?: boolean;
  /** Task click handler */
  onClick?: () => void;
  /** Task drag start handler */
  onDragStart?: (taskId: string) => void;
  /** Task drag end handler */
  onDragEnd?: (taskId: string, newStart: Date, newDuration: number) => void;
  /** Context menu handler */
  onContextMenu?: (taskId: string, event: React.MouseEvent) => void;
}
```

## Component State Management

### Presentational Components
- Receive all data via props
- Emit events via callback props
- No local state for external data
- Can have local state for UI interactions (open/close, hover, etc.)

### Container Components
- Manage data fetching and state
- Handle business logic
- Compose presentational components
- Connect to Redux store via hooks

### Example Container Pattern
```typescript
// Container Component
const ProjectListContainer: React.FC = () => {
  // Data fetching
  const { data: projects, loading, error } = useGetProjectsQuery();
  
  // Local state
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [filters, setFilters] = useState<ProjectFilters>({});
  
  // Event handlers
  const handleCreateProject = () => {
    navigate('/projects/create');
  };
  
  const handleProjectClick = (projectId: string) => {
    navigate(`/projects/${projectId}`);
  };
  
  // Render
  return (
    <ProjectList
      projects={projects}
      loading={loading}
      viewMode={viewMode}
      filters={filters}
      onProjectClick={handleProjectClick}
      onCreateProject={handleCreateProject}
      onViewModeChange={setViewMode}
      onFilterChange={setFilters}
    />
  );
};
```

---

*Component Architecture Specification v1.0*

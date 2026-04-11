# Mobile App Specification for Project Management System (PMS)

## 1. Complete Mobile Architecture Design

### 1.1 Technical Stack
- **Framework**: React Native (with TypeScript)
- **State Management**: Redux Toolkit + RTK Query
- **UI Library**: React Native Paper + NativeBase
- **Navigation**: React Navigation (Stack + Bottom Tabs)
- **Offline Support**: Redux Persist + AsyncStorage
- **Push Notifications**: Firebase Cloud Messaging (FCM)
- **Testing**: Jest + React Native Testing Library + Detox

### 1.2 Component Architecture
```
src/
├── assets/               # Static assets (images, fonts)
├── components/           # Reusable UI components
│   ├── ui/               # Basic UI elements (buttons, inputs)
│   ├── layout/           # Layout components (headers, footers)
│   └── shared/           # Shared components across features
├── features/             # Feature modules
│   ├── auth/             # Authentication flow
│   ├── projects/         # Project management
│   ├── tasks/            # Task management
│   └── notifications/    # Push notifications
├── navigation/           # Navigation setup
│   ├── AppNavigator.tsx  # Root navigator
│   └── BottomTabs.tsx    # Tab navigation
├── services/             # API and business logic
│   ├── api/              # API clients
│   └── sync/             # Offline sync logic
├── store/                # Redux store setup
│   ├── slices/           # Redux slices
│   └── hooks.ts          # Typed hooks
├── utils/                # Utility functions
└── App.tsx               # App entry point
```

### 1.3 Platform-Specific Considerations
- **iOS**:
  - SafeAreaView for notch support
  - HIG compliance for navigation patterns
- **Android**:
  - BackHandler integration
  - Material Design 3 compliance

---

## 2. Detailed Screen Specifications

### 2.1 Authentication Flow

#### 2.1.1 Login Screen
- **Layout**: Centered form with logo at top
- **Components**:
  - Email input field with validation (required, email format)
  - Password input field with toggle visibility
  - Remember me checkbox
  - Submit button (disabled until form valid)
  - Forgot password link
  - Social login buttons (Google, Apple) with loading states
- **Error States**:
  - Invalid credentials toast
  - Network error banner
- **Accessibility**:
  - Labels for all inputs
  - Minimum touch target 48dp

#### 2.1.2 Registration Screen
- **Layout**: Scrollable form
- **Components**:
  - Full name input (required, min 2 chars)
  - Email input with validation
  - Password input with strength indicator
  - Confirm password input with match validation
  - Terms and conditions checkbox with link
  - Submit button (disabled until form valid)
- **Validation**:
  - Real-time field validation
  - Password strength requirements (8+ chars, number, special char)
- **Accessibility**:
  - Error messages associated with inputs
  - Keyboard navigable form

#### 2.1.3 Password Reset Screen
- **Layout**: Simple centered form
- **Components**:
  - Email input with validation
  - Submit button
  - Back to login link
- **Success State**:
  - Confirmation message with return to login timer

### 2.2 Main App Screens

#### 2.2.1 Dashboard Screen
- **Layout**: Vertical scroll with cards
- **Components**:
  - **Stats Cards** (4-column grid on tablet, single column on phone):
    - Active Projects (with trend indicator)
    - Tasks Due Today
    - Overdue Tasks
    - Team Availability
  - **Recent Activity Feed**:
    - Grouped by project
    - Action icons (created, updated, commented)
    - Relative timestamps
    - Load more pagination
  - **Quick Actions** (bottom sheet on FAB press):
    - Create Project
    - Add Task
    - View Profile

#### 2.2.2 Projects List Screen
- **Layout**: Column-based with floating action button
- **Components**:
  - **Search Bar** (persistent at top):
    - Search by project name/description
    - Clear button
  - **Filter Chip Group** (horizontal scroll):
    - All Projects (default)
    - Active
    - Completed
    - Archived
    - My Projects
  - **Project List Items**:
    - Project avatar/color badge
    - Project name (truncated with tooltip)
    - Progress bar with percentage
    - Due date badge (red if overdue)
    - Team member avatars (max 3, +more indicator)
    - Menu button (⋮) for project actions
  - **Empty State**:
    - Illustration + guidance text
    - Primary button to create first project
  - **FAB** (bottom right):
    - Create new project
    - Long press for quick add

#### 2.2.3 Project Detail Screen
- **Layout**: Vertical tabs with swipe navigation
- **Tabs**:
  - **Overview** (default):
    - Project metadata (dates, status, priority)
    - Progress dashboard (completion %, burndown)
    - Upcoming milestones
    - Recent activity
  - **Gantt Chart**:
    - Touch-enabled timeline
    - Drag to adjust task dates
    - Pinch to zoom timeline
    - Double-tap to fit to screen
    - Task dependency lines (visual on connect)
    - Critical path highlighting
  - **Tasks**:
    - List view with grouping options (by assignee, status)
    - Swipe to change task status
    - Inline editing for task name/dates
    - Subtask indicator
  - **Team**:
    - Member avatars with roles
    - Availability indicators
    - Add/remove members (admin only)
  - **Files**:
    - Grid/list view toggle
    - File preview thumbnails
    - Download/share actions

#### 2.2.4 Task Management Screen
- **Layout**: Board view with columns
- **Views Toggle** (tabbed):
  - **Board (Kanban)**:
    - Columns: To Do, In Progress, Review, Done
    - Drag-and-drop between columns
    - Drag to reorder within column
    - Task cards show: assignee avatar, due date, priority
    - Long press for task menu
  - **List**:
    - Sortable by: due date, priority, assignee, created
    - Compact view for dense information
  - **Calendar**:
    - Month/week/day views
    - Dot indicators for task density
    - Tap to see daily tasks
- **Task Card Components**:
  - Primary color indicator (left border)
  - Task title (with overflow ellipsis)
  - Assignee avatars (max 2)
  - Due date/time (red if overdue/past due)
  - Priority indicator (dots or flags)
  - Progress circle for subtasks
- **Task Detail Modal** (bottom sheet):
  - Full task form with all fields
  - Subtasks list with reordering
  - Activity timeline
  - Comments section with threading
  - Attachments preview
  - Time tracking controls

#### 2.2.5 Notifications Screen
- **Layout**: Vertical list with grouped sections
- **Components**:
  - **Unread Badge Count** (header)
  - **Today** section:
    - Recent task notifications
    - Project updates
  - **Yesterday** section:
    - Older notifications
  - **Previous** section:
    - Collapsible older notifications
  - **Notification Item**:
    - Type icon (task, project, comment, assignment)
    - Title with bold keywords
    - Preview text (first line)
    - Timestamp (relative)
    - Unread indicator (blue dot)
    - Swipe to mark read/dismiss
  - **Empty State**:
    - "No notifications" message
    - Checkmark illustration
  - **Mark All Read** (sticky header, if unread exists)

#### 2.2.6 Profile Screen
- **Layout**: Settings-style vertical list
- **Sections**:
  - **Header**:
    - Profile picture (tap to update)
    - Name and role
    - Contact information
  - **Account Settings**:
    - Edit Profile button
    - Change Password button
    - Notification Preferences button
    - Language/Country selection
  - **App Settings**:
    - Dark Mode toggle
    - Data Saver mode
    - Clear cache button
  - **Support**:
    - Help Center button
    - Contact Support button
    - Feedback button
  - **Footer Actions**:
    - Log out (red text, warning confirmation)
    - Sign out of all devices

#### 2.2.7 Create/Edit Project Screen
- **Layout**: Scrollable form with sections
- **Fields**:
  - **Project Information** (required):
    - Project name (text, required, 3-100 chars)
    - Description (textarea, optional)
    - Color picker (6 preset colors + custom)
  - **Dates** (required):
    - Start date (date picker, required)
    - End date (date picker, required, must be after start)
    - Show milestone timeline checkbox
  - **Settings** (admin only):
    - Visibility (public/private)
    - Team access level
    - Archive date
  - **Actions** (fixed bottom):
    - Save as Draft (keeps form open)
    - Create Project (creates + goes to detail)
    - Cancel (confirmation dialog)
- **Validation**:
  - Required field indicators (red asterisk)
  - Inline validation errors
  - Prevent submission with invalid data
- **Loading States**:
  - Submit button with spinner
  - Screen dimming

#### 2.2.8 Create/Edit Task Screen
- **Layout**: Form with collapsible sections
- **Fields**:
  - **Task Details** (required):
    - Task title (text, required)
    - Description (rich text, optional)
    - Project selector (if creating from task view)
  - **Assignments**:
    - Assignee dropdown with search
    - Multiple assignee support
  - **Scheduling**:
    - Due date picker
    - Time picker (optional)
    - Reminders (1h, 1d, custom)
  - **Priority** (required):
    - Selector: High, Medium, Low
  - **Subtasks** (optional):
    - Add subtasks with check buttons
    - Reorder via drag handles
  - **Attachments**:
    - Camera icon
    - Gallery picker
    - Recent files quick access
  - **Tags/Labels**:
    - Multi-select dropdown
    - Create new tag option
- **Actions** (fixed bottom):
  - Save as Draft (optional, if enabled)
  - Create Task
  - Cancel

## 3. Navigation Flow with Transitions

#### 3.1 Navigation Structure
```
App Navigator (Stack)
├── Auth Stack (initial)
│   ├── LoginScreen
│   │   └── ForgotPasswordScreen
│   └── RegistrationScreen
└── Main Stack (after auth)
    ├── Main Tab Navigator
    │   ├── Dashboard Tab
    │   ├── Projects Tab
    │   ├── Tasks Tab
    │   └── Notifications Tab
    └── Feature Screens
        ├── ProjectDetailScreen
        │   ├── ProjectFormScreen (modal)
        │   └── TaskDetailScreen (modal)
        ├── TaskBoardScreen
        │   ├── TaskFormScreen (bottom sheet)
        │   └── TaskEditScreen (modal)
        └── SettingsScreen
            ├── ProfileEditScreen
            └── NotificationSettingsScreen
```

#### 3.2 Navigation Configuration
- **Stack Navigator**:
  - Default transition: `cardStyleInterpolator: 'forHorizontalIOS'`
  - Header styling: MUI theme-based
  - Back button: Platform-native
- **Tab Navigator**:
  - Type: `createBottomTabNavigator`
  - Icons: MUI icons with labels
  - Active color: Primary theme color
  - Inactive color: Gray 500
- **Modal Transitions**:
  - Type: `modal`
  - Gesture: Swipe down to dismiss (iOS), system back (Android)

#### 3.3 Transition Types

##### 3.3.1 Horizontal Slide (Standard Stack)
```typescript
// Default stack navigation
transitionSpec: {
  open: {
    animation: 'timing',
    config: { duration: 250 },
  },
  close: {
    animation: 'timing',
    config: { duration: 250 },
  },
},
cardStyleInterpolator: (props) => ({
  overlay: {
    opacity: `rgba(0, 0, 0, ${props.progress})`,
  },
  card: {
    transform: [{
      translateX: props.transitionProgress.interpolate({
        inputRange: [0, 1],
        outputRange: ['100%', 0],
      }),
    }],
  },
}),
```

##### 3.3.2 Fade (Modal Presentations)
```typescript
// Modal transitions
cardStyleInterpolator: 'fadeModal',
```

##### 3.3.3 Slide Up (Bottom Sheets)
```typescript
// Task detail bottom sheet
cardStyleInterpolator: (props) => ({
  card: {
    transform: [{
      translateY: props.position.interpolate({
        inputRange: [-1, 0],
        outputRange: ['100%', 0],
      }),
    }],
  },
}),
```

##### 3.3.4 No Transition (Tab Switching)
```typescript
// Tab navigation
animationEnabled: false,
```

#### 3.4 Navigation Actions Map
| Action | Transition | Animation |
|--------|-----------|-----------|
| Login → Main | Stack | Horizontal slide right |
| Main → Project Detail | Stack | Horizontal slide right |
| Project List → Create Project | Modal | Fade in + scale up |
| Project Detail → Project Edit | Bottom Sheet | Slide up from bottom |
| Task Board → Task Detail | Bottom Sheet | Slide up from bottom |
| All Tabs → Feature Screen | Stack | Horizontal slide right |
| Feature Screen → Close | Pop | Horizontal slide left |
| Deep link to notification | Stack + Reset | Horizontal slide right |

#### 3.5 Deep Linking Configuration
```typescript
linking: {
  prefixes: ['pms://'],
  config: {
    screens: {
      Login: 'login',
      Projects: 'projects',
      ProjectDetail: 'projects/:projectId',
      TaskDetail: 'tasks/:taskId',
      Notifications: 'notifications',
      NotificationDetail: 'notifications/:notificationId',
      Profile: 'profile',
    },
  },
},
```

#### 3.6 Back Navigation Handling
```typescript
// Android back button handling
useFocusEffect(
  React.useCallback(() => {
    const onBackPress = () => {
      if (canGoBack()) {
        goBack();
        return true;
      }
      // Confirm exit if on home screen
      if (isHomeScreen) {
        Alert.alert(
          'Exit App',
          'Are you sure you want to exit?',
          [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Exit',
              onPress: () => ExitHandler.exitApp(),
            },
          ]
        );
        return true;
      }
      return false;
    };

    const subscription = BackHandler.addEventListener(
      'hardwareBackPress',
      onBackPress
    );

    return () => subscription.remove();
  }, [canGoBack, isHomeScreen])
);
```

#### 3.7 Navigation State Persistence
```typescript
// Persist navigation state to AsyncStorage
const persistence = {
  storage: new AsyncStoragePersistence({
    key: 'nav_state',
    version: 1,
  }),
};
```

#### 3.8 Navigation Guards
- **Auth Guard**: Redirect unauthenticated users to Login
- **Role Guard**: Redirect unauthorized roles based on permissions
- **Dirty Form Guard**: Prompt if unsaved changes exist before navigation
- **Loading Guard**: Disable navigation during critical API operations

## 4. API Integration Strategy

#### 4.1 Client Architecture
```typescript
// src/services/api/client.ts
export const apiClient = {
  // Base configuration
  baseURL: 'https://api.pms.example.com/v1',
  timeout: 15000, // 15 second timeout
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  // Auth token injection
  authInterceptor: (token: string) => {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  },
};

// Interceptors
apiClient.interceptors.request.use(
  async (config) => {
    // Add request ID for tracing
    config.headers['X-Request-ID'] = generateRequestId();
    // Add device info
    config.headers['X-Device-Info'] = JSON.stringify({
      platform: Platform.OS,
      version: Platform.Version,
      model: DeviceInfo.getDeviceName(),
    });
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle token expiration
    if (error.response?.status === 401) {
      return handleTokenRefresh(error.config);
    }
    // Handle network errors
    if (!navigator.onLine) {
      return handleOfflineRequest(error.config);
    }
    return Promise.reject(error);
  }
);
```

#### 4.2 RTK Query Setup
```typescript
// src/store/api/pmsApi.ts
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const pmsApi = createApi({
  reducerPath: 'pmsApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.token;
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: [
    'Projects',
    'Tasks',
    'Notifications',
    'Users',
    'Dashboard',
  ],
  endpoints: (builder) => ({
    // Authentication
    login: builder.mutation<LoginResponse, LoginRequest>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
      transformResponse: (response: LoginResponse) => ({
        ...response,
        expiresAt: Date.now() + response.expiresIn * 1000,
      }),
    }),
    refreshToken: builder.mutation<RefreshResponse, void>({
      query: () => ({
        url: '/auth/refresh',
        method: 'POST',
      }),
    }),
    
    // Projects
    getProjects: builder.query<Project[], GetProjectsParams>({
      query: (params) => ({
        url: '/projects',
        params,
      }),
      providesTags: ['Projects'],
    }),
    getProject: builder.query<Project, string>({
      query: (projectId) => `/projects/${projectId}`,
      providesTags: (result, error, projectId) => [{ type: 'Projects', id: projectId }],
    }),
    createProject: builder.mutation<Project, CreateProjectInput>({
      query: (body) => ({
        url: '/projects',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Projects', 'Dashboard'],
    }),
    updateProject: builder.mutation<Project, UpdateProjectInput>({
      query: ({ projectId, ...body }) => ({
        url: `/projects/${projectId}`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: (result, error, { projectId }) => [{ type: 'Projects', id: projectId }],
    }),
    deleteProject: builder.mutation<void, string>({
      query: (projectId) => ({
        url: `/projects/${projectId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Projects', 'Dashboard'],
    }),
    
    // Tasks
    getTasks: builder.query<Task[], GetTasksParams>({
      query: (params) => ({
        url: '/tasks',
        params,
      }),
      providesTags: ['Tasks'],
    }),
    updateTaskStatus: builder.mutation<Task, UpdateTaskStatusInput>({
      query: (body) => ({
        url: '/tasks/status',
        method: 'PATCH',
        body,
      }),
      invalidatesTags: ['Tasks', 'Dashboard'],
    }),
    
    // Notifications
    getNotifications: builder.query<Notification[], GetNotificationsParams>({
      query: (params) => ({
        url: '/notifications',
        params,
      }),
      providesTags: ['Notifications'],
    }),
    markNotificationRead: builder.mutation<void, string>({
      query: (notificationId) => ({
        url: `/notifications/${notificationId}/read`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Notifications'],
    }),
    
    // Dashboard
    getDashboard: builder.query<DashboardData, void>({
      query: () => '/dashboard',
      providesTags: ['Dashboard'],
    }),
  }),
});

export const {
  useLoginMutation,
  useRefreshTokenMutation,
  useGetProjectsQuery,
  useGetProjectQuery,
  useCreateProjectMutation,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
  useGetTasksQuery,
  useUpdateTaskStatusMutation,
  useGetNotificationsQuery,
  useMarkNotificationReadMutation,
  useGetDashboardQuery,
} = pmsApi;
```

#### 4.3 Endpoint Mapping
| Feature | API Endpoint | HTTP Method | Cache TTL |
|---------|-------------|-------------|-----------|
| Login | `/auth/login` | POST | N/A |
| Refresh Token | `/auth/refresh` | POST | N/A |
| Get Projects | `/projects` | GET | 30s |
| Get Project | `/projects/:id` | GET | 60s |
| Create Project | `/projects` | POST | N/A |
| Update Project | `/projects/:id` | PATCH | N/A |
| Delete Project | `/projects/:id` | DELETE | N/A |
| Get Tasks | `/tasks` | GET | 15s |
| Update Task Status | `/tasks/status` | PATCH | N/A |
| Get Notifications | `/notifications` | GET | 30s |
| Mark Read | `/notifications/:id/read` | PATCH | N/A |
| Dashboard | `/dashboard` | GET | 15s |

#### 4.4 Error Handling Strategy
```typescript
// Error response handler
export const handleApiError = (error: ApiError): AppError => {
  if (error.code === 'NETWORK_ERROR') {
    return {
      message: 'Network error. Please check your connection.',
      type: 'network',
      retryable: true,
    };
  }
  
  if (error.response?.status === 401) {
    return {
      message: 'Session expired. Please log in again.',
      type: 'unauthorized',
      retryable: false,
    };
  }
  
  if (error.response?.status === 403) {
    return {
      message: 'You do not have permission to perform this action.',
      type: 'forbidden',
      retryable: false,
    };
  }
  
  if (error.response?.status === 409) {
    return {
      message: 'A conflict occurred. Please try again.',
      type: 'conflict',
      retryable: true,
    };
  }
  
  if (error.response?.status >= 500) {
    return {
      message: 'Server error. Please try again later.',
      type: 'server_error',
      retryable: true,
    };
  }
  
  return {
    message: error.response?.data?.message || 'An unexpected error occurred.',
    type: 'unknown',
    retryable: false,
  };
};
```

#### 4.5 Retry Strategy
```typescript
// Retry configuration
const retryConfig = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 5000,
  backoffMultiplier: 2,
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
};

// Retry logic implementation
export const retryableRequest = async <T>(
  requestFn: () => Promise<T>,
  config: RetryConfig = retryConfig
): Promise<T> => {
  let lastError: Error;
  
  for (let attempt = 0; attempt < config.maxRetries; attempt++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error as Error;
      const isRetryable = config.retryableStatusCodes.includes(
        (error as ApiError)?.response?.status
      );
      
      if (!isRetryable || attempt === config.maxRetries - 1) {
        throw error;
      }
      
      const delay = Math.min(
        config.initialDelay * Math.pow(config.backoffMultiplier, attempt),
        config.maxDelay
      );
      
      await sleep(delay);
    }
  }
  
  throw lastError;
};
```

#### 4.6 Caching Strategy
```typescript
// RTK Query cache configuration
const cacheConfig = {
  // Default settings
  defaultCache: {
    staleTime: 30000, // 30 seconds
    gcTime: 300000,   // 5 minutes
  },
  
  // Endpoint-specific overrides
  overrides: {
    // Real-time data (notifications)
    getNotifications: {
      staleTime: 10000, // 10 seconds
      gcTime: 60000,    // 1 minute
    },
    // Stable data (projects)
    getProjects: {
      staleTime: 60000, // 1 minute
      gcTime: 600000,   // 10 minutes
    },
    // Dashboard (frequently updated)
    getDashboard: {
      staleTime: 15000, // 15 seconds
      gcTime: 300000,   // 5 minutes
    },
  },
};
```

#### 4.7 Request Deduplication
```typescript
// Prevent duplicate in-flight requests
const pendingRequests = new Map<string, Promise<any>>();

export const dedupedRequest = <T>(
  key: string,
  requestFn: () => Promise<T>
): Promise<T> => {
  const pending = pendingRequests.get(key);
  if (pending) {
    return pending;
  }
  
  const promise = requestFn().finally(() => {
    pendingRequests.delete(key);
  });
  
  pendingRequests.set(key, promise);
  return promise;
};
```

#### 4.8 Request Cancellation
```typescript
// Cancel active requests on unmount
const useCancelOnUnmount = () => {
  const controllerRef = useRef<AbortController | null>(null);
  
  useEffect(() => {
    controllerRef.current = new AbortController();
    return () => {
      controllerRef.current?.abort();
    };
  }, []);
  
  return controllerRef.current?.signal;
};

// Usage in component
const signal = useCancelOnUnmount();
const { data, error } = useGetDashboardQuery(undefined, {
  skip: !isLoggedIn,
  signal,
});
```

## 5. Offline-First Considerations

#### 5.1 Offline Architecture Overview
```typescript
// Offline-first architecture
┌─────────────────────────────────────────────────────────┐
│                     Mobile App                          │
├─────────────────────────────────────────────────────────┤
│  Application Layer                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  RTK Query Cache (Stale-While-Revalidate)       │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Redux Store with Persist                       │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Persistence Layer                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  AsyncStorage + WatermelonDB (SQLite)            │   │
│  │  - Projects                                       │   │
│  │  - Tasks                                          │   │
│  │  - Notifications                                  │   │
│  │  - User Settings                                  │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Sync Layer                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Background Sync Queue                            │   │
│  │  - Pending operations                              │   │
│  │  - Conflict resolution                             │   │
│  │  - Sync status tracking                            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

#### 5.2 Data Synchronization Strategy
```typescript
// Sync configuration
export interface SyncConfig {
  // Network monitoring
  onlineDetector: () => Promise<boolean>;
  
  // Queue management
  maxQueueSize: number;
  autoSyncInterval: number; // ms
  
  // Retry logic
  syncRetryAttempts: number;
  syncRetryDelay: number;
  
  // Conflict resolution
  strategy: 'server-wins' | 'client-wins' | 'merge';
}

const syncConfig: SyncConfig = {
  onlineDetector: () => {
    return new Promise((resolve) => {
      NetworkConnection.addEventListener(
        'change',
        (connection) => resolve(connection?.type !== 'none')
      );
    });
  },
  maxQueueSize: 100,
  autoSyncInterval: 60000, // 1 minute
  syncRetryAttempts: 5,
  syncRetryDelay: 10000,
  strategy: 'server-wins',
};
```

#### 5.3 Pending Operations Queue
```typescript
// Queue model
export interface PendingOperation {
  id: string;
  type: 'CREATE' | 'UPDATE' | 'DELETE';
  entity: 'PROJECT' | 'TASK' | 'NOTIFICATION';
  entityId: string;
  data: Record<string, unknown>;
  timestamp: number;
  retryCount: number;
  lastAttempt: number | null;
  error: string | null;
}

// Queue management service
class SyncQueue {
  private queue: PendingOperation[] = [];
  
  add(operation: PendingOperation): void {
    if (this.queue.length >= syncConfig.maxQueueSize) {
      throw new Error('Queue is full');
    }
    this.queue.push({
      ...operation,
      timestamp: Date.now(),
    });
    this.saveQueue();
  }
  
  async process(): Promise<void> {
    if (!await this.isOnline()) return;
    
    const operations = [...this.queue];
    this.queue = [];
    this.saveQueue();
    
    for (const operation of operations) {
      try {
        await this.executeOperation(operation);
      } catch (error) {
        if (operation.retryCount < syncConfig.syncRetryAttempts) {
          this.add({
            ...operation,
            retryCount: operation.retryCount + 1,
            lastAttempt: Date.now(),
            error: error.message,
          });
        }
      }
    }
  }
  
  private async executeOperation(operation: PendingOperation): Promise<void> {
    // Execute the actual API call
    switch (operation.type) {
      case 'CREATE':
        await createEntity(operation.entity, operation.data);
        break;
      case 'UPDATE':
        await updateEntity(operation.entity, operation.entityId, operation.data);
        break;
      case 'DELETE':
        await deleteEntity(operation.entity, operation.entityId);
        break;
    }
  }
}
```

#### 5.4 Network Connection Detection
```typescript
// Network status monitoring
class NetworkMonitor {
  private unsubscribe: (() => void) | null = null;
  private statusListener: ((isOnline: boolean) => void) | null = null;
  
  constructor() {
    this.startMonitoring();
  }
  
  startMonitoring(): void {
    this.unsubscribe = NetworkConnection.addEventListener(
      'change',
      (status) => {
        this.emitStatusChange(status !== 'none');
      }
    );
  }
  
  onStatusChange(listener: (isOnline: boolean) => void): void {
    this.statusListener = listener;
  }
  
  private emitStatusChange(isOnline: boolean): void {
    this.statusListener?.(isOnline);
    
    if (isOnline) {
      // Trigger sync when coming online
      SyncService.syncPendingOperations();
    }
  }
  
  destroy(): void {
    this.unsubscribe?.();
  }
}
```

#### 5.5 Local Data Caching Strategy
```typescript
// Data model with last modified timestamp
interface CachedEntity {
  id: string;
  data: unknown;
  updatedAt: number;
  serverVersion: number;
  isDeleted: boolean;
}

// Entity-specific caches
const caches = {
  projects: new Map<string, CachedEntity>(),
  tasks: new Map<string, CachedEntity>(),
  notifications: new Map<string, CachedEntity>(),
};

// Cache update strategy
export const updateCache = <T extends { id: string }>(
  entity: T,
  cacheType: 'projects' | 'tasks' | 'notifications'
): void => {
  const cached = caches[cacheType].get(entity.id);
  
  if (!cached || entity.updatedAt > cached.updatedAt) {
    caches[cacheType].set(entity.id, {
      id: entity.id,
      data: entity,
      updatedAt: entity.updatedAt,
      serverVersion: entity.version || 1,
      isDeleted: false,
    });
    saveToStorage();
  }
};

// Cache read with staleness check
export const getFromCache = <T>(
  id: string,
  cacheType: 'projects' | 'tasks' | 'notifications',
  maxStaleness: number = 60000
): T | null => {
  const cached = caches[cacheType].get(id);
  
  if (!cached || cached.isDeleted) return null;
  
  const isStale = Date.now() - cached.updatedAt > maxStaleness;
  
  if (isStale) {
    // Trigger background refresh
    triggerBackgroundRefresh(cacheType, id);
  }
  
  return cached.data as T;
};
```

#### 5.6 Conflict Resolution Strategy
```typescript
// Conflict resolution types
export type ConflictStrategy = 
  | 'server-wins'      // Server version always takes precedence
  | 'client-wins'      // Client version takes precedence
  | 'merge'            // Smart merge of changes
  | 'manual'           // User is prompted to choose
  
// Merge strategy implementation
export const resolveConflict = (
  serverData: unknown,
  clientData: unknown,
  strategy: ConflictStrategy = 'server-wins'
): unknown => {
  switch (strategy) {
    case 'server-wins':
      return serverData;
      
    case 'client-wins':
      return clientData;
      
    case 'merge':
      return mergeObjects(serverData, clientData);
      
    case 'manual':
      return {
        needsManualResolution: true,
        serverVersion: serverData,
        clientVersion: clientData,
      };
      
    default:
      return serverData;
  }
};

// Smart merge for nested objects
const mergeObjects = (
  server: Record<string, unknown>,
  client: Record<string, unknown>
): Record<string, unknown> => {
  const merged = { ...server };
  
  for (const [key, value] of Object.entries(client)) {
    if (
      typeof value === 'object' &&
      typeof merged[key] === 'object' &&
      !Array.isArray(value) &&
      !Array.isArray(merged[key])
    ) {
      merged[key] = mergeObjects(
        merged[key] as Record<string, unknown>,
        value as Record<string, unknown>
      );
    } else {
      merged[key] = value;
    }
  }
  
  return merged;
};
```

#### 5.7 Background Sync Implementation
```typescript
// Background sync service
class SyncService {
  private static instance: SyncService;
  
  private constructor() {}
  
  static getInstance(): SyncService {
    if (!SyncService.instance) {
      SyncService.instance = new SyncService();
    }
    return SyncService.instance;
  }
  
  async syncPendingOperations(): Promise<void> {
    const pendingOps = await SyncQueue.getPendingOperations();
    
    for (const operation of pendingOps) {
      try {
        await SyncQueue.execute(operation);
      } catch (error) {
        SyncQueue.markFailed(operation, error.message);
      }
    }
  }
  
  async syncProjectData(projectId: string): Promise<void> {
    // Pull latest data from server
    const { data } = await apiClient.get(`/projects/${projectId}`);
    await updateCache(data, 'projects');
    
    // Sync tasks
    const { data: tasks } = await apiClient.get(
      `/projects/${projectId}/tasks`
    );
    for (const task of tasks) {
      await updateCache(task, 'tasks');
    }
  }
}

// Use React Native Background Fetch
import BackgroundFetch from 'react-native-background-fetch';

BackgroundFetch.configure(
  {
    minimumInterval: 15 * 60, // 15 minutes (iOS limit)
    stopOnTerminate: false,
    startOnBoot: true,
  },
  async (taskId) => {
    // Background sync
    await SyncService.syncPendingOperations();
    BackgroundFetch.finish(taskId);
  },
  (errorMessage) => {
    console.error('Background fetch error:', errorMessage);
  }
);
```

#### 5.8 Offline States UI
```typescript
// Offline indicator component
export const OfflineIndicator: React.FC = () => {
  const isOnline = useNetworkStatus();
  
  if (isOnline) return null;
  
  return (
    <AlertBanner
      variant="warning"
      icon={Warning}
      title="You're offline"
      message="Changes will sync when you're back online"
    />
  );
};

// Sync status indicator
export const SyncStatusIndicator: React.FC = () => {
  const pendingOps = usePendingOperationsCount();
  const isSyncing = useIsSyncing();
  
  if (pendingOps === 0 && !isSyncing) return null;
  
  return (
    <FAB
      icon={isSyncing ? 'sync' : 'alert'}
      onPress={() => SyncService.syncPendingOperations()}
      style={styles.syncFab}
    >
      {pendingOps > 0 && (
        <Badge variant="dot">{pendingOps}</Badge>
      )}
    </FAB>
  );
};

// Loading state management
const useLoadingStates = (
  query: UseQueryResult,
  hasPendingOps: boolean
) => {
  const isLoading = query.isLoading || hasPendingOps;
  const isFetching = query.isFetching;
  
  return { isLoading, isFetching };
};
```

#### 5.9 Data Consistency Guarantees
```typescript
// Consistency levels
export const consistencyLevels = {
  // Strong consistency for critical operations
  strong: ['CREATE_PROJECT', 'DELETE_PROJECT', 'UPDATE_TASK_STATUS'],
  
  // Eventual consistency for less critical operations
  eventual: ['UPDATE_TASK_TITLE', 'ADD_COMMENT', 'VIEW_DASHBOARD'],
};

// Operation priority
export const operationPriorities = {
  high: ['CREATE_PROJECT', 'DELETE_PROJECT'],
  medium: ['UPDATE_TASK_STATUS', 'CREATE_TASK'],
  low: ['UPDATE_PROJECT_NAME', 'ADD_COMMENT'],
};

// Transaction support for related operations
class SyncTransaction {
  private operations: PendingOperation[] = [];
  
  begin(): void {
    this.operations = [];
  }
  
  add(operation: PendingOperation): void {
    this.operations.push(operation);
  }
  
  async commit(): Promise<void> {
    // Execute operations in order
    for (const op of this.operations) {
      await SyncQueue.add(op);
    }
    
    // Mark as batched for atomic sync
    await markAsBatch(this.operations);
  }
  
  async rollback(): Promise<void> {
    // Remove all pending operations
    this.operations = [];
  }
}
```

## 6. Push Notification Strategy

#### 6.1 Notification Architecture
```
┌─────────────────────────────────────────────────────────┐
│              Push Notification Flow                     │
├─────────────────────────────────────────────────────────┤
│  Server Side (FCM)                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Firebase Cloud Messaging                        │   │
│  │  - Token management                               │   │
│  │  - Message routing                                │   │
│  │  - Delivery tracking                              │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Mobile Client                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  FCM Integration                                  │   │
│  │  - Token registration                             │   │
│  │  - Message handling                               │   │
│  │  - Local notifications                            │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Notification Service                             │   │
│  │  - Priority routing                               │   │
│  │  - Action handling                                │   │
│  │  - In-app display                                 │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

#### 6.2 FCM Configuration
```typescript
// FCM initialization
import messaging from '@react-native-firebase/messaging';

export const initializeFCM = async (): Promise<string> => {
  // Request permissions
  const authStatus = await messaging().requestPermission();
  
  const enabled =
    authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
    authStatus === messaging.AuthorizationStatus.PROVISIONAL;
  
  if (!enabled) {
    console.warn('Push notifications not enabled');
    return '';
  }
  
  // Get FCM token
  const token = await messaging().getToken();
  
  // Save token to server
  await saveDeviceToken(token);
  
  // Set up token refresh listener
  messaging().onTokenRefresh((newToken) => {
    saveDeviceToken(newToken);
  });
  
  return token;
};

// Save device token
const saveDeviceToken = async (token: string): Promise<void> => {
  await apiClient.post('/devices/token', {
    token,
    platform: Platform.OS,
    deviceId: DeviceInfo.getUniqueId(),
  });
};
```

#### 6.3 Notification Types
```typescript
// Notification type definitions
export const NotificationType = {
  PROJECT_CREATED: 'project_created',
  PROJECT_UPDATED: 'project_updated',
  PROJECT_DELETED: 'project_deleted',
  TASK_ASSIGNED: 'task_assigned',
  TASK_UPDATED: 'task_updated',
  TASK_DUE_SOON: 'task_due_soon',
  TASK_OVERDUE: 'task_overdue',
  TASK_COMPLETED: 'task_completed',
  COMMENT_ADDED: 'comment_added',
  ATTACHMENT_UPLOADED: 'attachment_uploaded',
  MILESTONE_REACHED: 'milestone_reached',
  TEAM_MEMBER_ADDED: 'team_member_added',
  TEAM_MEMBER_REMOVED: 'team_member_removed',
  MENTIONED: 'mentioned',
  SYSTEM: 'system',
} as const;

// Notification payloads
interface NotificationPayload {
  type: keyof typeof NotificationType;
  title: string;
  body: string;
  data: Record<string, unknown>;
  sound?: string;
  badge?: number;
  priority?: 'high' | 'normal';
  ttl?: number;
  collapseKey?: string;
}

// Type-specific handlers
const notificationHandlers: Record<
  keyof typeof NotificationType,
  (payload: NotificationPayload) => void
> = {
  [NotificationType.TASK_ASSIGNED]: (payload) => {
    // Task assigned - high priority
    showNotification({
      title: 'New Task Assigned',
      body: payload.body,
      action: 'viewTask',
      taskId: payload.data.taskId,
    });
  },
  [NotificationType.TASK_DUE_SOON]: (payload) => {
    // Task due soon - medium priority
    showNotification({
      title: 'Task Due Soon',
      body: payload.body,
      action: 'viewTask',
      taskId: payload.data.taskId,
    });
  },
  [NotificationType.COMMENT_ADDED]: (payload) => {
    // Comment added - normal priority
    showNotification({
      title: 'New Comment',
      body: payload.body,
      action: 'viewComment',
      commentId: payload.data.commentId,
    });
  },
  // ... other handlers
};
```

#### 6.4 Notification Priorities
```typescript
// Priority levels
const notificationPriorities = {
  // Immediate display, override Do Not Disturb (iOS), top priority (Android)
  critical: [
    NotificationType.TASK_OVERDUE,
    NotificationType.MENTIONED,
    NotificationType.SYSTEM,
  ],
  // High priority, appears in lock screen
  high: [
    NotificationType.TASK_ASSIGNED,
    NotificationType.TASK_DUE_SOON,
    NotificationType.PROJECT_UPDATED,
  ],
  // Normal priority, may be batched
  normal: [
    NotificationType.COMMENT_ADDED,
    NotificationType.TASK_UPDATED,
    NotificationType.TASK_COMPLETED,
    NotificationType.ATTACHMENT_UPLOADED,
  ],
  // Low priority, batched with other low-priority notifications
  low: [
    NotificationType.PROJECT_CREATED,
    NotificationType.MILESTONE_REACHED,
    NotificationType.TEAM_MEMBER_ADDED,
    NotificationType.TEAM_MEMBER_REMOVED,
  ],
};

// Map notification type to priority
const getNotificationPriority = (
  type: keyof typeof NotificationType
): 'critical' | 'high' | 'normal' | 'low' => {
  if (notificationPriorities.critical.includes(type)) return 'critical';
  if (notificationPriorities.high.includes(type)) return 'high';
  if (notificationPriorities.normal.includes(type)) return 'normal';
  return 'low';
};

// Build FCM message with priority
const buildFcmMessage = (payload: NotificationPayload): FcmMessage => {
  const priority = getNotificationPriority(payload.type);
  
  return {
    to: deviceToken,
    data: payload.data,
    notification: {
      title: payload.title,
      body: payload.body,
      sound: getSoundForType(payload.type),
      badge: calculateBadgeCount(),
      click_action: getClickAction(payload),
    },
    priority: priority === 'critical' ? 'max' : 'normal',
    ttl: payload.ttl ?? getTtlForPriority(priority),
  };
};
```

#### 6.5 Notification Handlers
```typescript
// Notification handlers for foreground/background states
export const setupNotificationHandlers = (): void => {
  // Foreground notification handler
  messaging().onMessage(async (remoteMessage) => {
    await handleForegroundNotification(remoteMessage);
  });
  
  // Background notification handler (iOS)
  messaging().setBackgroundMessageHandler(async (remoteMessage) => {
    await handleBackgroundNotification(remoteMessage);
  });
  
  // Notification opened handler
  const initialNotification = await messaging().getInitialNotification();
  if (initialNotification) {
    handleNotificationOpened(initialNotification);
  }
  
  // Listen for notification opened events
  messaging().onNotificationOpenedApp((remoteMessage) => {
    handleNotificationOpened(remoteMessage);
  });
  
  // Token refresh handler
  messaging().onTokenRefresh((token) => {
    saveDeviceToken(token);
  });
};

// Handle foreground notification
const handleForegroundNotification = async (
  remoteMessage: RemoteMessage
): Promise<void> => {
  const { data, notification } = remoteMessage;
  
  // Show in-app notification
  showInAppNotification({
    title: notification?.title || 'Notification',
    body: notification?.body || '',
    data,
  });
  
  // Update notification count
  await incrementNotificationCount();
  
  // Play sound if app is in foreground
  if (Platform.OS === 'ios') {
    // iOS handles sound via notification configuration
  } else {
    // Android: custom sound handling
    playNotificationSound(getSoundForType(data.type));
  }
};

// Handle background notification (Android)
const handleBackgroundNotification = async (
  remoteMessage: RemoteMessage
): Promise<void> => {
  // Process notification data in background
  const { data } = remoteMessage;
  
  if (data.type === NotificationType.TASK_OVERDUE) {
    // Mark as critical, create local notification
    createLocalNotification({
      title: data.title,
      body: data.body,
      data,
      priority: 'max',
    });
  } else {
    // Update notification badge count
    updateBadgeCount();
  }
};

// Handle notification tap
const handleNotificationOpened = (
  remoteMessage: RemoteMessage
): void => {
  const { data } = remoteMessage;
  
  // Navigate to appropriate screen based on notification type
  switch (data.type) {
    case NotificationType.TASK_ASSIGNED:
    case NotificationType.TASK_UPDATED:
    case NotificationType.TASK_COMPLETED:
      navigateTo('TaskDetail', { taskId: data.taskId });
      break;
      
    case NotificationType.PROJECT_UPDATED:
    case NotificationType.PROJECT_CREATED:
      navigateTo('ProjectDetail', { projectId: data.projectId });
      break;
      
    case NotificationType.COMMENT_ADDED:
      navigateTo('TaskDetail', {
        taskId: data.taskId,
        scrollToComment: data.commentId,
      });
      break;
      
    case NotificationType.MENTIONED:
      navigateTo('TaskDetail', {
        taskId: data.taskId,
        scrollToComment: data.commentId,
      });
      break;
      
    default:
      navigateTo('Notifications');
  }
};
```

#### 6.6 Local Notifications
```typescript
// Local notification library
import PushNotification from 'react-native-push-notification';

// Configure local notifications
PushNotification.configure({
  // Should the initial notification pop up when the app is opened
  onNotification: function (notification) {
    handleLocalNotification(notification);
  },
  
  permissions: {
    alert: true,
    badge: true,
    sound: true,
  },
  
  // Request permission on iOS
  popInitialNotification: true,
  requestPermissions: true,
});

// Create local notification
export const createLocalNotification = (
  notification: CreateNotificationParams
): void => {
  const {
    title,
    body,
    data,
    priority = 'high',
    sound = true,
    badge = true,
    bigText = null,
  } = notification;
  
  PushNotification.localNotification({
    title,
    message: body,
    data,
    soundName: sound ? getSoundForNotificationType(data?.type) : null,
    importance: getAndroidImportance(priority),
    vibrate: true,
    vibration: 300,
    priority: getAndroidPriority(priority),
    sticky: false,
    allowWhileIdle: true,
    bigText,
    badge,
  });
};

// Create scheduled notification (e.g., task due reminders)
export const scheduleLocalNotification = (
  params: ScheduleNotificationParams
): void => {
  const {
    date,
    title,
    body,
    data,
    message,
  } = params;
  
  PushNotification.localNotificationSchedule({
    date: new Date(date),
    title,
    message,
    data,
    allowWhileIdle: true,
    bigText: body,
  });
};

// Handle local notification tap
const handleLocalNotification = (notification: any): void => {
  if (notification.userInteraction) {
    // User tapped the notification
    handleNotificationOpened({
      data: notification.data,
    });
  }
  
  // Clear notification after handling
  notification.finish(PushNotificationios.FetchResult.NoData);
};

// Get Android notification importance
const getAndroidImportance = (priority: string): string => {
  switch (priority) {
    case 'critical':
      return 'max';
    case 'high':
      return 'high';
    case 'normal':
      return 'default';
    default:
      return 'low';
  }
};

// Get Android notification priority
const getAndroidPriority = (priority: string): string => {
  switch (priority) {
    case 'critical':
      return 'high';
    case 'high':
      return 'high';
    default:
      return 'normal';
  }
};
```

#### 6.7 Notification Permissions
```typescript
// Permission management
class NotificationPermission {
  static async request(): Promise<boolean> {
    if (Platform.OS === 'ios') {
      return this.requestIOSPermissions();
    } else {
      return this.requestAndroidPermissions();
    }
  }
  
  static async requestIOSPermissions(): Promise<boolean> {
    const authStatus = await messaging().requestPermission();
    
    return (
      authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
      authStatus === messaging.AuthorizationStatus.PROVISIONAL
    );
  }
  
  static async requestAndroidPermissions(): Promise<boolean> {
    const granted = await PushNotification.requestPermissions({
      permissions: ['alert', 'badge', 'sound'],
    });
    
    return (
      granted.alert === 'granted' &&
      granted.badge === 'granted' &&
      granted.sound === 'granted'
    );
  }
  
  static async check(): Promise<boolean> {
    if (Platform.OS === 'ios') {
      const status = await messaging().getDeviceAPNSDeviceToken();
      return !!status;
    } else {
      const granted = await PushNotification.checkPermissions();
      return granted.alert === 'granted';
    }
  }
  
  static async openSettings(): Promise<void> {
    if (Platform.OS === 'ios') {
      Linking.openURL(Linking.URLs.appSettings);
    } else {
      Linking.openSettings();
    }
  }
}

// Permission request UI component
export const PermissionRequestBanner: React.FC<{
  onAllow: () => void;
  onDeny: () => void;
}> = ({ onAllow, onDeny }) => {
  const [show, setShow] = useState(true);
  
  return show ? (
    <Banner
      variant="info"
      title="Enable Notifications"
      description="Stay updated with task assignments, updates, and team activities"
      actionLabel="Enable"
      secondaryLabel="Maybe Later"
      onAction={async () => {
        const granted = await NotificationPermission.request();
        if (granted) {
          setShow(false);
          onAllow();
        } else {
          onDeny();
        }
      }}
      onSecondaryAction={() => {
        setShow(false);
        onDeny();
      }}
    />
  ) : null;
};
```

#### 6.8 Notification In-App Display
```typescript
// In-app notification component
export const InAppNotification: React.FC<{
  notification: Notification;
  onDismiss: (id: string) => void;
  onAction?: (notification: Notification) => void;
}> = ({ notification, onDismiss, onAction }) => {
  const [animated, setAnimated] = useState(false);
  
  useEffect(() => {
    // Animate notification in
    setTimeout(() => setAnimated(true), 100);
    
    // Auto-dismiss after 5 seconds
    const timer = setTimeout(() => {
      onDismiss(notification.id);
    }, 5000);
    
    return () => clearTimeout(timer);
  }, [notification.id, onDismiss]);
  
  return (
    <Animated.View
      style={[
        styles.container,
        {
          opacity: animated ? 1 : 0,
          transform: [
            {
              translateY: animated ? 0 : -100,
            },
          ],
        },
      ]}
    >
      <TouchableOpacity
        style={styles.wrapper}
        onPress={() => onAction?.(notification)}
      >
        <View style={styles.iconContainer}>
          <Icon source={getIconForType(notification.type)} />
        </View>
        <View style={styles.content}>
          <Text style={styles.title}>{notification.title}</Text>
          <Text style={styles.body} numberOfLines={2}>
            {notification.body}
          </Text>
        </View>
        <TouchableOpacity
          style={styles.dismiss}
          onPress={() => onDismiss(notification.id)}
        >
          <Icon source={Icons.close} />
        </TouchableOpacity>
      </TouchableOpacity>
      
      {/* Progress bar for auto-dismiss */}
      <ProgressBar
        progress={0}
        color="primary"
        style={styles.progressBar}
      />
    </Animated.View>
  );
};

// Notification toast/snackbar system
const showNotification = (
  notification: Omit<Notification, 'id' | 'createdAt'>
): void => {
  const id = generateUUID();
  
  const newNotification: Notification = {
    ...notification,
    id,
    createdAt: Date.now(),
    read: false,
  };
  
  // Add to Redux store
  dispatch(addNotification(newNotification));
  
  // Show toast
  showToast({
    title: notification.title,
    message: notification.body,
    type: getToastType(notification.type),
  });
};
```

#### 6.9 Notification Settings
```typescript
// Notification preference schema
export interface NotificationPreferences {
  // Global toggle
  enabled: boolean;
  
  // Category-based settings
  categories: {
    [key in keyof typeof NotificationType]?: {
      enabled: boolean;
      sound: boolean;
      vibration: boolean;
      badge: boolean;
    };
  };
  
  // Time-based settings (Do Not Disturb)
  dnd: {
    enabled: boolean;
    startTime: string; // HH:MM
    endTime: string; // HH:MM
    days: number[]; // 0=Sunday, 6=Saturday
  };
  
  // Silent hours for critical notifications
  criticalNotificationsAlways: boolean;
}

// Default preferences
const defaultPreferences: NotificationPreferences = {
  enabled: true,
  categories: {
    [NotificationType.TASK_ASSIGNED]: {
      enabled: true,
      sound: true,
      vibration: true,
      badge: true,
    },
    [NotificationType.COMMENT_ADDED]: {
      enabled: true,
      sound: true,
      vibration: false,
      badge: false,
    },
    [NotificationType.TASK_DUE_SOON]: {
      enabled: true,
      sound: true,
      vibration: false,
      badge: true,
    },
    // Default to enabled for all
    [NotificationType.PROJECT_CREATED]: {
      enabled: true,
      sound: false,
      vibration: false,
      badge: true,
    },
    [NotificationType.SYSTEM]: {
      enabled: true,
      sound: true,
      vibration: true,
      badge: true,
    },
  },
  dnd: {
    enabled: false,
    startTime: '22:00',
    endTime: '07:00',
    days: [1, 2, 3, 4, 5], // Weekdays only
  },
  criticalNotificationsAlways: false,
};

// Check if notification should be sent
const shouldSendNotification = (
  type: keyof typeof NotificationType,
  preferences: NotificationPreferences
): boolean => {
  // Global toggle
  if (!preferences.enabled) return false;
  
  // Do Not Disturb check
  if (
    preferences.dnd.enabled &&
    isWithinDndTime(preferences.dnd) &&
    !preferences.criticalNotificationsAlways
  ) {
    return false;
  }
  
  // Category-specific settings
  const categorySettings = preferences.categories[type];
  if (categorySettings) {
    return categorySettings.enabled;
  }
  
  return true;
};
```

---

---

---
---

## 3. Navigation Flow with Transitions

### 3.1 Navigation Structure
- **Auth Stack**: Login → Register → Reset Password
- **Main Tabs**: Dashboard ↔ Projects ↔ Tasks ↔ Notifications
- **Project Flow**: List → Detail → Task View

### 3.2 Transition Types
- **Horizontal Slide**: For stack navigation
- **Fade**: For modal presentations
- **None**: For tab switches

---

## 4. API Integration Strategy

### 4.1 Client Architecture
- **RTK Query**: For API calls and caching
- **Offline Queue**: For deferred actions
- **Automatic Retries**: For failed requests

### 4.2 Endpoint Mapping
- `/auth/*`: Authentication endpoints
- `/projects/*`: Project management
- `/tasks/*`: Task operations

---

## 5. Offline-First Considerations

### 5.1 Data Persistence
- **Redux Persist**: For state hydration
- **AsyncStorage**: For local data storage

### 5.2 Sync Strategy
1. **Optimistic Updates**: UI updates immediately
2. **Queue Management**: Failed requests retried
3. **Conflict Resolution**: Timestamp-based merging

---

## 6. Push Notification Strategy

### 6.1 Notification Types
- **Task Assignments**: "You've been assigned a task"
- **Due Date Reminders**: "Task due in 24 hours"
- **Project Updates**: "New comment on Project X"

### 6.2 Handling
- **Foreground**: In-app toast
- **Background**: System notification
- **Tapping**: Deep link to relevant screen

---

## 7. Mobile-Specific UI/UX Patterns

### 7.1 Gestures
- **Swipe to Archive**: For tasks/projects
- **Pull to Refresh**: For lists

### 7.2 Adaptive Components
- **Bottom Sheet**: For actions/forms
- **Snackbars**: For transient messages

---

## 8. Comprehensive Test Strategy

### 8.1 Test Pyramid
- **Unit**: 70% coverage (Jest)
- **Integration**: 20% (React Native Testing Library)
- **E2E**: 10% (Detox)

### 8.2 Key Test Cases
1. **Auth Flow**: Successful login/logout
2. **Offline Mode**: Queue management
3. **Notification Handling**: Deep linking

---

*Specification Version: 1.0*
*Last Updated: $(date)*